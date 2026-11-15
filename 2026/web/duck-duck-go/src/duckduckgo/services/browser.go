package services

import (
	"errors"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"

	"database/sql"

	"github.com/beego/beego/v2/client/orm"
	"github.com/fatduck/duckduckgo/constants"
	"github.com/fatduck/duckduckgo/models"
	"github.com/go-rod/rod"
	"github.com/go-rod/rod/lib/launcher"
	_ "github.com/mattn/go-sqlite3"
	"mvdan.cc/xurls/v2"
)

type BrowserScanner struct {
	CurrentRecursion int
	Scan             *models.Scan
	Settings         *models.ScanSettings
	Browser          *rod.Browser
	DB               *sql.DB
	ResultsTable     string
}

func (b *BrowserScanner) Initialise() (err error) {
	u := launcher.New().
		Bin(constants.ChromiumPath).
		Headless(true).
		Leakless(false).
		Set("no-sandbox").
		Set("disable-gpu").
		Set("disable-dev-shm-usage").
		Set("crash-dumps-dir", "/tmp/chrome-crashes").
		Set("--incognito").
		MustLaunch()
	b.Browser = rod.New().ControlURL(u).MustConnect().Timeout(15 * time.Second)
	b.CurrentRecursion = 0

	st, err := url.Parse(b.Scan.TargetUrl)
	if err != nil || (st.Scheme != "http" && st.Scheme != "https") {
		return errors.New("Invalid target url")
	}

	folder := filepath.Join(constants.ScansFolder, b.Scan.Username)

	if _, err := os.Stat(folder); err != nil {
		os.Mkdir(folder, 0755)
	}

	b.Scan.OutputDatabase = filepath.Join(folder, st.Host+b.Settings.DatabaseSuffix)

	return b.setupDatabase()
}

func (b *BrowserScanner) setupDatabase() (err error) {
	b.DB, err = sql.Open("sqlite3", b.Scan.OutputDatabase)
	if err != nil {
		return err
	}

	resultstbl := b.Settings.TablePrefix + "results"
	badwordtbl := b.Settings.TablePrefix + "badwords"
	b.ResultsTable = resultstbl

	if !ValidTableName(resultstbl) || !ValidTableName(badwordtbl) {
		return errors.New("Invalid table name detects")
	}

	sqlStmt := fmt.Sprintf(`
	CREATE TABLE IF NOT EXISTS %s (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		url TEXT NOT NULL,
		matched_bad_word TEXT NOT NULL
	);
	
	CREATE TABLE %s (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		bad_word TEXT NOT NULL
	);

	CREATE INDEX idx_badwords_bad_word ON %s (bad_word);
    `, resultstbl, badwordtbl, badwordtbl)

	_, err = b.DB.Exec(sqlStmt)
	if err != nil {
		return err
	}

	for _, bw := range b.Settings.GetBadWords() {
		sqlStmt = fmt.Sprintf(`INSERT OR IGNORE INTO %s (bad_word) VALUES (?);`, badwordtbl)

		_, err = b.DB.Exec(sqlStmt, bw)
		if err != nil {
			return err
		}
	}

	return nil
}

func (b *BrowserScanner) StartScan() {
	defer func() {
		if r := recover(); r != nil {
			fmt.Println("oopsie i panicked:", r)
		}
		if b.DB != nil {
			_ = b.DB.Close()
		}
		if b.Browser != nil {
			_ = b.Browser.CancelTimeout().Close()
		}
		b.Scan.Completed = true
		o := orm.NewOrm()
		_, _ = o.Update(b.Scan)
	}()
	b.browserScan(b.Scan.TargetUrl)
}

func (b *BrowserScanner) browserScan(t string) {
	tp, err := url.Parse(t)
	if err != nil {
		return
	}
	if tp.Scheme != "https" && tp.Scheme != "http" {
		return
	}
	p := b.Browser.MustPage(t)
	defer func() { _ = p.Close() }()
	html, err := p.HTML()
	if err != nil {
		return
	}

	if b.CurrentRecursion < b.Settings.RecursionDepth {
		b.CurrentRecursion++
		rxStrict := xurls.Strict()
		urls := rxStrict.FindAllString(html, -1)
		for _, u := range urls {
			b.browserScan(u)
		}
	}

	for _, bad := range b.Settings.GetBadWords() {
		if strings.Contains(html, bad) {
			b.addResult(t, bad)
		}
	}
}

func (b *BrowserScanner) addResult(t string, bad string) (err error) {
	sqlStmt := fmt.Sprintf(`INSERT OR IGNORE INTO %s (url, matched_bad_word) VALUES (?);`, b.ResultsTable)
	_, err = b.DB.Exec(sqlStmt, t, bad)
	if err != nil {
		return err
	}
	return nil
}

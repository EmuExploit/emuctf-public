package services

import (
	"errors"
	"fmt"
	"net/url"
	"regexp"
	"strings"

	"github.com/beego/beego/v2/client/orm"
	"github.com/fatduck/duckduckgo/models"
)

func MakeDefaultScanSettings(username string) (err error) {
	ss := models.ScanSettings{
		Username:       username,
		DatabaseSuffix: "_scan.sqlite",
		TablePrefix:    "",
		RecursionDepth: 1,
	}
	bw := []string{
		"pigeon",
		"coo",
		"duckin ducks",
		"free bread crumbs",
		"poop on statues",
		"grit",
		"breadcrumbs",
		"urban",
		"seed funding",
		"rooftop",
		"statue-friendly",
		"Built for flock-scale deployment",
		"Sky-native infrastructure",
		"Decentralized breadcrumb acquisition",
		"Enterprise-grade coo systems",
		"Powered by wing-driven analytics",
		"potential food sources",
	}
	ss.SetBadWords(bw)
	o := orm.NewOrm()
	_, err = o.Insert(&ss)
	return err
}

func HasScanSettings(username string) bool {
	_, err := GetScanSettings(username)
	return err == nil
}

func GetScanSettings(username string) (s *models.ScanSettings, err error) {
	o := orm.NewOrm()
	s = new(models.ScanSettings)
	s.Username = username
	err = o.Read(s, "Username")
	return s, err
}

func UpdateScanSettings(username string, dbsfx string, tblpfx string, badwords []string) (err error) {
	if strings.Contains(dbsfx, "..") {
		return errors.New("Database suffix must not contain '..'.")
	}

	if !ValidTableName(tblpfx) {
		return errors.New("Invalid tablename prefix, must match ^[a-zA-Z0-9_]*$")
	}

	s, err := GetScanSettings(username)
	if err != nil {
		return err
	}

	s.DatabaseSuffix = dbsfx
	s.TablePrefix = tblpfx
	s.SetBadWords(badwords)

	o := orm.NewOrm()
	_, err = o.Update(s)
	return err
}

func ScanUrl(username string, t string) (err error) {
	turl, err := url.Parse(t)
	if err != nil {
		return err
	}

	if turl.Scheme != "http" && turl.Scheme != "https" {
		return errors.New("Must provide a http or https URL")
	}

	settings, err := GetScanSettings(username)

	scan := new(models.Scan)
	scan.Username = username
	scan.TargetUrl = t
	scan.Completed = false
	o := orm.NewOrm()
	_, err = o.Insert(scan)
	if err != nil {
		o.Delete(scan)
		return errors.New("Failed to initialise scan")
	}

	b := BrowserScanner{
		Scan:     scan,
		Settings: settings,
	}
	err = b.Initialise()
	if err != nil {
		fmt.Println(err)
		o.Delete(scan)
		return errors.New("Failed to initialise scan")
	}

	go b.StartScan()
	return nil
}

func GetScan(username string, id int) (scan *models.Scan, err error) {
	scan = new(models.Scan)
	scan.Username = username
	scan.Id = id
	o := orm.NewOrm()
	err = o.Read(scan, "Username", "Id")
	if err != nil {
		return nil, err
	}
	return scan, nil
}

func ListScans(username string) (scans *[]models.Scan, err error) {
	o := orm.NewOrm()

	scans = new([]models.Scan)

	_, err = o.QueryTable(new(models.Scan)).Filter("Username", username).All(scans)
	if err != nil {
		fmt.Println(err)
		return nil, err
	}

	return scans, nil
}

func ValidTableName(tblname string) bool {
	match, err := regexp.MatchString("^[a-zA-Z0-9_]*$", tblname)
	if !match || err != nil {
		return false
	}
	return true
}

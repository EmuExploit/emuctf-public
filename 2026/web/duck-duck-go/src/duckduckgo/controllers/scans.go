package controllers

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/fatduck/duckduckgo/constants"
	"github.com/fatduck/duckduckgo/services"
)

type ScansController struct {
	BaseController
}

func (c *ScansController) Get() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}

	scans, err := services.ListScans(uname)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
		c.Redirect("/user/me", 302)
		return
	}
	c.TplName = "pages/scans.html"
	c.Data["Title"] = "Scans"
	c.Data["Username"] = uname
	c.Data["Flash"] = c.GetSession(constants.FlashKey)
	c.Data["Errors"] = c.GetSession(constants.ErrorKey)
	c.Data["Scans"] = scans
	c.DelSession(constants.FlashKey)
	c.DelSession(constants.ErrorKey)
}

func (c *ScansController) StartScan() {
	uname, ok := c.CurrentUser()
	if !ok {
		c.ClearSession()
		c.SetSession(constants.ErrorKey, "Invalid session.")
		c.Redirect("/login", 302)
		return
	}
	target := c.GetString("target")
	err := services.ScanUrl(uname, target)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
	} else {
		c.SetSession(constants.FlashKey, fmt.Sprintf("Scanning %s", target))
	}

	c.Redirect("/scans", 302)
}

func (c *ScansController) GetSettings() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}
	settings, err := services.GetScanSettings(uname)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
		c.Redirect("/scans", 302)
		return
	}

	c.TplName = "pages/scan-settings.html"
	c.Data["Title"] = "Scan Settings"
	c.Data["Errors"] = c.GetSession(constants.ErrorKey)
	c.Data["Flash"] = c.GetSession(constants.FlashKey)
	c.Data["Username"] = uname
	c.Data["Settings"] = settings
	c.Data["BadWords"] = settings.GetBadWords()
	c.DelSession(constants.FlashKey)
	c.DelSession(constants.ErrorKey)
}

func (c *ScansController) UpdateSettings() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}
	dbsfx := c.GetString("database_suffix")
	tblpfx := c.GetString("table_prefix")
	badwords := c.GetStrings("badwords")

	err := services.UpdateScanSettings(uname, dbsfx, tblpfx, badwords)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
	} else {
		c.SetSession(constants.FlashKey, "Updated scanner settings")
	}
	c.Redirect("/scans/settings", 302)
}

func (c *ScansController) Download() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}

	sid, err := c.GetInt("scan_id")
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
		c.Redirect("/scans", 302)
		return
	}
	scan, err := services.GetScan(uname, sid)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
		c.Redirect("/scans", 302)
		return
	}

	if !scan.Completed {
		c.SetSession(constants.ErrorKey, "That scan has not completed yet!")
		c.Redirect("/scans", 302)
		return
	}

	if _, err := os.Stat(scan.OutputDatabase); err != nil {
		c.SetSession(constants.ErrorKey, "What dah duck? That DB file doesn't exist")
		c.Redirect("/scans", 302)
		return
	}

	// this is safe, since usernames can only be alphanumeric
	folder := filepath.Join(constants.ScansFolder, uname) + string(filepath.Separator)

	if !strings.HasPrefix(filepath.Clean(scan.OutputDatabase), folder) {
		c.SetSession(constants.ErrorKey, "Gotchya you smelly pigeon!")
		c.Redirect("/scans", 302)
		return
	}

	c.Ctx.Output.Download(scan.OutputDatabase, filepath.Base(scan.OutputDatabase))
}

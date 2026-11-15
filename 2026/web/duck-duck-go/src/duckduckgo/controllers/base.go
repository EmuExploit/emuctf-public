package controllers

import (
	"github.com/beego/beego/v2/server/web"
	"github.com/fatduck/duckduckgo/constants"
)

type BaseController struct {
	web.Controller
}

func (c *BaseController) Prepare() {
	c.Layout = "layouts/base.html"
	c.Data["LayoutDesign"] = "app-layout"
}

func (c *BaseController) CurrentUser() (username string, ok bool) {
	u := c.GetSession(constants.SessionKey)
	if u == nil {
		c.ClearSession()
		c.SetSession(constants.ErrorKey, "Invalid session.")
		c.Redirect("/login", 302)
		return "", false
	}
	return u.(string), true
}

func (c *BaseController) SetCurrentUser(uname string) {
	c.SetSession(constants.SessionKey, uname)
}

func (c *BaseController) ClearSession() {
	c.DelSession(constants.SessionKey)
}

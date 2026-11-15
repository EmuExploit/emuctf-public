package controllers

import (
	"strings"

	"github.com/fatduck/duckduckgo/constants"
	"github.com/fatduck/duckduckgo/services"
)

type AuthController struct {
	BaseController
}

func (c *AuthController) GetRegister() {
	if u := c.GetSession(constants.SessionKey); u != nil {
		c.Redirect("/user/me", 302)
		return
	}
	c.TplName = "pages/register.html"
	c.Data["Title"] = "Create Account"
	c.Data["Flash"] = c.GetSession(constants.FlashKey)
	c.Data["LayoutDesign"] = "auth-layout"
	c.DelSession(constants.FlashKey)
}

func (c *AuthController) PostRegister() {
	if u := c.GetSession(constants.SessionKey); u != nil {
		c.Redirect("/user/me", 302)
		return
	}
	username := strings.TrimSpace(c.GetString("username"))
	password := c.GetString("password")
	confirm := c.GetString("confirm_password")

	errs := services.Register(username, password, confirm)
	if len(errs) > 0 {
		c.TplName = "pages/register.html"
		c.Data["Title"] = "Create Account"
		c.Data["Errors"] = errs
		c.Data["Username"] = username
		c.Data["LayoutDesign"] = "auth-layout"
		return
	}

	c.SetSession(constants.FlashKey, "Account created! Please log in.")
	c.Redirect("/login", 302)
}

func (c *AuthController) GetLogin() {
	if u := c.GetSession(constants.SessionKey); u != nil {
		c.Redirect("/user/me", 302)
		return
	}
	c.TplName = "pages/login.html"
	c.Data["Title"] = "Sign In"
	c.Data["Flash"] = c.GetSession(constants.FlashKey)
	c.Data["LayoutDesign"] = "auth-layout"
	c.DelSession(constants.FlashKey)
}

func (c *AuthController) PostLogin() {
	if u := c.GetSession(constants.SessionKey); u != nil {
		c.Redirect("/user/me", 302)
		return
	}
	username := strings.TrimSpace(c.GetString("username"))
	password := c.GetString("password")

	err := services.Authenticate(username, password)
	if err != nil {
		c.TplName = "pages/login.html"
		c.Data["Title"] = "Sign In"
		c.Data["Errors"] = []string{err.Error()}
		c.Data["Username"] = username
		c.Data["LayoutDesign"] = "auth-layout"
		return
	}

	c.SetCurrentUser(username)

	c.Redirect("/user/me", 302)
}

func (c *AuthController) Logout() {
	c.ClearSession()
	c.Redirect("/login", 302)
}

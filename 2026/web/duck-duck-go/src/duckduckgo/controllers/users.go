package controllers

import (
	"github.com/fatduck/duckduckgo/constants"
	"github.com/fatduck/duckduckgo/services"
)

type UserController struct {
	BaseController
}

func (c *UserController) Me() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}
	u, issub, err := services.GetUserAndHasSubscribePlan(uname)
	if err != nil {
		c.ClearSession()
		c.SetSession(constants.ErrorKey, "Invalid session.")
		c.Redirect("/login", 302)
		return
	}

	c.TplName = "pages/me.html"
	c.Data["Title"] = "Profile"
	errMsg := c.GetString("error")
	if errMsg != "" {
		c.Data["Errors"] = errMsg
	} else {
		c.Data["Errors"] = c.GetSession(constants.ErrorKey)
	}
	c.Data["Username"] = u.Username
	c.Data["IsSub"] = issub
	c.DelSession(constants.ErrorKey)
}

func (c *UserController) GetSubscription() {
	c.SetSession(constants.ErrorKey, "Sorry, we have locked online subscription enrolment for now. Contact sales if you want to purchase a plan.")
	c.Redirect("/users/me", 302)
}

func (c *UserController) UpdateMyPassword() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}
	origpass := c.GetString("origpass")
	newpass := c.GetString("newpass")
	err := services.UpdatePassword(uname, origpass, newpass)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
	}
	c.Redirect("/user/me", 302)
}

func (c *UserController) DeleteMe() {
	uname, ok := c.CurrentUser()
	if !ok {
		return
	}
	services.DeleteUser(uname)
}

func (c *UserController) List() {
	users, err := services.ListUsers()
	errString := c.GetSession(constants.ErrorKey)
	c.DelSession(constants.ErrorKey)
	if err != nil {
		errString = err.Error()
	}
	c.TplName = "pages/admin/listusers.html"
	c.Data["Title"] = "Admin"
	c.Data["Errors"] = errString
	c.Data["Users"] = users
}

func (c *UserController) Delete() {
	uname := c.GetString("username")
	err := services.DeleteUser(uname)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
	}
	c.Redirect("/admin/users", 302)
}

func (c *UserController) AddSubscriptionPlan() {
	uname := c.GetString("username")
	err := services.AddSubscriptionPlan(uname)
	if err != nil {
		c.SetSession(constants.ErrorKey, err.Error())
	}
	c.Redirect("/admin/users", 302)
}

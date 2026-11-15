package controllers

type IndexController struct {
	BaseController
}

func (c *IndexController) Index() {
	_, ok := c.CurrentUser()
	if ok {
		c.Redirect("/user/me", 302)
		return
	}
	c.Redirect("/login", 302)
}

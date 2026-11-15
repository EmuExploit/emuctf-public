package routes

import (
	"github.com/beego/beego/v2/server/web"
	"github.com/fatduck/duckduckgo/controllers"
	"github.com/fatduck/duckduckgo/middleware"
)

func registerAdminRoutes() {
	web.InsertFilter("/admin/*", web.BeforeRouter, middleware.AdminMiddleware)

	web.Router("/admin/users", &controllers.UserController{}, "get:List")
	web.Router("/admin/users/delete", &controllers.UserController{}, "delete:Delete")
	web.Router("/admin/users/subscriber", &controllers.UserController{}, "post:AddSubscriptionPlan")
}

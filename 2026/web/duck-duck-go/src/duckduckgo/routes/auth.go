package routes

import (
	"github.com/beego/beego/v2/server/web"
	"github.com/fatduck/duckduckgo/controllers"
	"github.com/fatduck/duckduckgo/middleware"
)

func registerAuthRoutes() {
	web.InsertFilter("/user/*", web.BeforeRouter, middleware.AuthMiddleware)
	web.InsertFilter("/logout", web.BeforeRouter, middleware.AuthMiddleware)

	web.Router("/user/me", &controllers.UserController{}, "get:Me")
	web.Router("/user/update-password", &controllers.UserController{}, "post:UpdateMyPassword")
	web.Router("/user/delete", &controllers.UserController{}, "delete:DeleteMe")

	web.Router("/logout", &controllers.AuthController{}, "get:Logout")
}

package routes

import (
	"github.com/beego/beego/v2/server/web"
	"github.com/fatduck/duckduckgo/controllers"
)

func registerUnauthRoutes() {
	web.Router("/", &controllers.IndexController{}, "get:Index")

	web.Router("/register", &controllers.AuthController{}, "get:GetRegister;post:PostRegister")
	web.Router("/login", &controllers.AuthController{}, "get:GetLogin;post:PostLogin")
}

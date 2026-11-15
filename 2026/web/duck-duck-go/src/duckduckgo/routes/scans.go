package routes

import (
	"github.com/beego/beego/v2/server/web"
	"github.com/fatduck/duckduckgo/controllers"
	"github.com/fatduck/duckduckgo/middleware"
)

func registerSubscriberRoutes() {
	web.InsertFilter("/scans/*", web.BeforeRouter, middleware.HasSubscriptionPlanMiddleware)

	web.Router("/scans", &controllers.ScansController{}, "get:Get;post:StartScan")
	web.Router("/scans/settings", &controllers.ScansController{}, "get:GetSettings;post:UpdateSettings")
	web.Router("/scans/download", &controllers.ScansController{}, "get:Download")
}

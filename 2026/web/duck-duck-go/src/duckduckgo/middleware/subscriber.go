package middleware

import (
	"net/url"

	"github.com/beego/beego/v2/server/web/context"
	"github.com/fatduck/duckduckgo/constants"
	"github.com/fatduck/duckduckgo/services"
)

func HasSubscriptionPlanMiddleware(ctx *context.Context) {
	AuthMiddleware(ctx)
	uname, ok := ctx.Input.Session(constants.SessionKey).(string)
	if !ok {
		ctx.Redirect(302, "/login")
		return
	}
	if !services.HasSubscriptionPlan(uname) {
		msg := url.QueryEscape("You do not have a valid subscription plan ya pleb! Pay me monies!")
		ctx.Redirect(302, "/user/me?error="+msg)
	}
}

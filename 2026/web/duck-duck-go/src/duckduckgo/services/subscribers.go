package services

import (
	"github.com/beego/beego/v2/client/orm"
	"github.com/fatduck/duckduckgo/models"
)

func HasSubscriptionPlan(username string) (issub bool) {
	o := orm.NewOrm()
	s := models.SubscriptionPlan{Username: username}
	o.Read(&s, "Username")
	return s.Id != 0
}

func AddSubscriptionPlan(username string) (err error) {
	o := orm.NewOrm()
	s := models.SubscriptionPlan{Username: username}
	_, err = o.Insert(&s)
	if err != nil {
		return err
	}
	if !HasScanSettings(username) {
		err = MakeDefaultScanSettings(username)
	}
	return err
}

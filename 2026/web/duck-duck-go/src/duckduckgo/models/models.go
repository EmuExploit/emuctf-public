package models

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"os"

	"github.com/beego/beego/v2/client/orm"
	"github.com/fatduck/duckduckgo/constants"
	_ "github.com/lib/pq"
)

func init() {
	orm.RegisterDriver("postgres", orm.DRPostgres)
	orm.RegisterDataBase("default", "postgres", os.Getenv("DATABASE_URL"))

	orm.RegisterModel(new(User))
	orm.RegisterModel(new(Scan))
	orm.RegisterModel(new(ScanSettings))
	orm.RegisterModel(new(SubscriptionPlan))

	orm.RunSyncdb("default", false, false)
}

func InitialiseAdmin() (err error) {
	o := orm.NewOrm()
	u := new(User)
	u.Username = constants.AdminUsername
	err = o.Read(u, "Username")
	if err == nil {
		fmt.Println("admin user has already been created")
		return nil
	}
	letters := "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-"
	n := 64
	ret := make([]byte, n)
	for i := 0; i < n; i++ {
		num, err := rand.Int(rand.Reader, big.NewInt(int64(len(letters))))
		if err != nil {
			return err
		}
		ret[i] = letters[num.Int64()]
	}

	u = new(User)
	u.Username = constants.AdminUsername
	u.Password = string(ret)
	_, err = o.Insert(u)
	return err
}

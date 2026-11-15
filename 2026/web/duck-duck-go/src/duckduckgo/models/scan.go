package models

type Scan struct {
	Id              int
	Username        string
	TargetUrl       string
	DetectedBadword bool
	OutputDatabase  string
	Completed       bool
}

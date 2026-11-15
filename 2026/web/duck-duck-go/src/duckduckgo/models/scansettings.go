package models

import "strings"

type ScanSettings struct {
	Id             int
	Username       string
	DatabaseSuffix string
	TablePrefix    string
	RecursionDepth int
	BadWords       string
}

func (m *ScanSettings) GetBadWords() (badwords []string) {
	return strings.Split(m.BadWords, "|")
}

func (m *ScanSettings) SetBadWords(badwords []string) {
	m.BadWords = strings.Join(badwords, "|")
}

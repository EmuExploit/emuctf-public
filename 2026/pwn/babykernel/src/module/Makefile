CWD := $(shell pwd)

obj-m += vuln.o
 
all:
	$(MAKE) -C $(CWD)/../linux M=$(CWD) modules

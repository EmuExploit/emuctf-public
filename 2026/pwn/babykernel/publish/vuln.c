#include <linux/init.h>
#include <linux/module.h>
#include <linux/device.h>
#include <linux/miscdevice.h>
#include <linux/fs.h>
#include <linux/mm.h>

#define DEV_NAME "vuln"

MODULE_AUTHOR("toasterpwn");
MODULE_DESCRIPTION("pwn me :)");
MODULE_LICENSE("GPL");

static struct miscdevice dev;

static int dev_open(struct inode* inodep, struct file* filp);
static int dev_mmap(struct file* filp, struct vm_area_struct* vma);
	
static struct file_operations dev_fops = {
	.owner = THIS_MODULE,
	.open = dev_open,
	.mmap = dev_mmap,
};

static int dev_open(struct inode* inodep, struct file* filp) { 
	return 0;
}

static int dev_mmap(struct file* filp, struct vm_area_struct* vma) {
	unsigned long size = vma->vm_end - vma->vm_start;

	vm_flags_set(vma, VM_IO | VM_DONTEXPAND | VM_DONTDUMP);
	vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot);

	if (remap_pfn_range(vma, vma->vm_start, vma->vm_pgoff, size, vma->vm_page_prot)) {
        	pr_err("[vuln] failed to map\n");
        	return -EAGAIN;
    	}

	return 0;
}

static int dev_init(void) {
	int ret = 0;
	
	dev.minor = MISC_DYNAMIC_MINOR;
	dev.name = DEV_NAME;
	dev.fops = &dev_fops;
	dev.mode = 0666;

	ret = misc_register(&dev);
	if (ret) {
		pr_err("[vuln] Failed to register device.");
        	return ret;
    	}
    
	pr_info("[vuln] Booting up.\n");
	
	return 0;
}


static void dev_cleanup(void) {
	misc_deregister(&dev);

	pr_info("[vuln] Shutting down.\n");
}


module_init(dev_init);
module_exit(dev_cleanup);

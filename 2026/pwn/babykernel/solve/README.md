# pwn/babykernel

The vulnerable kernel module passes our `mmap` page offset to `remap_pfn_range` directly, as the pfn. This gives us an abritrary physical mapping primitive.


We can use this to map `sys_setuid` and patch out the capability check:

```
   0xffffffff812b46e2 <+66>:	call   0xffffffff812a58f0 <ns_capable_setid>
   0xffffffff812b46e7 <+71>:	test   al,al
   0xffffffff812b46e9 <+73>:	je     0xffffffff812b4765 <__sys_setuid+197>
```

By NOPing 4 bytes ar +71, the capability check is skipped and we can set our UID to 0 and read the flag

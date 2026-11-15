# gdb -q -batch -x solve/update.gdb publish/main
set debuginfod enabled off
set pagination off
break _24_update
commands
  silent
  set language c++
  # frame register = shr->stackPointer on entry; frame[-9] = 1st argument (NaN-boxed object)
  set $ta  = (hermes::vm::JSTypedArrayBase *)(((SHRuntime *)$rdi)->stackPointer[-9].raw & 0xffffffffffff)
  set $buf = (hermes::vm::JSArrayBuffer *)$ta->buffer_.raw
  printf "update(%u bytes): ", $ta->length_
  output/c *($buf->data_ + $ta->offset_)@$ta->length_
  echo \n
  continue
end
run

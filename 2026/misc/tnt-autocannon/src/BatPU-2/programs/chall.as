.start
// frame 1: "CPU GO BRR"
LDI r15 clear_chars_buffer
STR r15 r0
LDI r15 write_char
LDI r14 "C"
STR r15 r14
LDI r14 "P"
STR r15 r14
LDI r14 "U"
STR r15 r14
LDI r14 " "
STR r15 r14
LDI r14 "G"
STR r15 r14
LDI r14 "O"
STR r15 r14
LDI r14 " "
STR r15 r14
LDI r14 "B"
STR r15 r14
LDI r14 "R"
STR r15 r14
LDI r14 "R"
STR r15 r14
LDI r15 buffer_chars
STR r15 r0
CAL .delay

// frame 2: "AND BOOM!"
LDI r15 clear_chars_buffer
STR r15 r0
LDI r15 write_char
LDI r14 "A"
STR r15 r14
LDI r14 "N"
STR r15 r14
LDI r14 "D"
STR r15 r14
LDI r14 " "
STR r15 r14
LDI r14 "B"
STR r15 r14
LDI r14 "O"
STR r15 r14
LDI r14 "O"
STR r15 r14
LDI r14 "M"
STR r15 r14
LDI r14 "!"
STR r15 r14
LDI r15 buffer_chars
STR r15 r0
CAL .delay

JMP .start

.delay
RET
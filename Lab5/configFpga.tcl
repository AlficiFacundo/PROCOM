
# Complete with Project info
set FPGAID 210319A28998A
set BITNAME fpga
set APPNAME upFW
set HWNAME microP
set WORKSPACEPATH "C:/Users/facun/vivadoProjects/workspaceP2026"
##############################################################

puts "FPGA: $FPGAID"
puts "WorkSpace: $WORKSPACEPATH"

connect -url tcp:127.0.0.1:3121
targets -set -filter {jtag_cable_name =~ "Digilent Arty $FPGAID" && level==0 && jtag_device_ctx=="jsn-Arty-$FPGAID-0362d093-0"}
fpga -file $WORKSPACEPATH/$APPNAME/_ide/bitstream/$BITNAME.bit

targets -set -nocase -filter {name =~ "*microblaze*#0" && bscan=="USER2"  && jtag_cable_name =~ "Digilent Arty $FPGAID" && jtag_device_ctx=="jsn-Arty-$FPGAID-0362d093-0"}
loadhw -hw $WORKSPACEPATH/$HWNAME/export/$HWNAME/hw/$BITNAME.xsa -regs
configparams mdm-detect-bscan-mask 2

targets -set -nocase -filter {name =~ "*microblaze*#0" && bscan=="USER2"  && jtag_cable_name =~ "Digilent Arty $FPGAID" && jtag_device_ctx=="jsn-Arty-$FPGAID-0362d093-0"}
rst -system
after 3000

targets -set -nocase -filter {name =~ "*microblaze*#0" && bscan=="USER2"  && jtag_cable_name =~ "Digilent Arty $FPGAID" && jtag_device_ctx=="jsn-Arty-$FPGAID-0362d093-0"}
dow $WORKSPACEPATH/$APPNAME/build/$APPNAME.elf

targets -set -nocase -filter {name =~ "*microblaze*#0" && bscan=="USER2"  && jtag_cable_name =~ "Digilent Arty $FPGAID" && jtag_device_ctx=="jsn-Arty-$FPGAID-0362d093-0"}
con
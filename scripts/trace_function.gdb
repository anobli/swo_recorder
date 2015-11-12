set $dwt_ctrl=0xE0001000
set $dwt_cyccnt=0xE0001004
set $itm_tcr=0xE0000E80

define gdbserver_connect
	# Connect to JLink
	tar ext :2331
end

define pc_sample_enable
	set *$dwt_cyccnt=64
	set *$dwt_ctrl|=0x00001001
end

define pc_sample_disable
	set *$dwt_cyccnt=0
	set *$dwt_ctrl&=~0x00001001
end

define exception_enable
	set *$dwt_ctrl|=0x00010000
end

define exception_disable
	set *$dwt_ctrl&=~0x00010000
end

define timestamp_enable
	set *$itm_tcr|=0x00000012
end

define timestamp_disable
	set *$itm_tcr&=~0x00000012
end
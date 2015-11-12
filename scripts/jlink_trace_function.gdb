define swo_start
	# FIXME these frequencies will only work with TSB MCU
	moni SWO EnableTarget 48000000 49230768 0xff 0
end

define swo_stop
	moni SWO DisableTarget 0xff
end
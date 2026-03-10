use uo;

function sendDiff(who, diff)
	if(!GetObjProperty(who, "toggleDiff"))
		Sendsysmessage(who, "Difficulty: "+diff);
	endif
return;
endfunction

function sendSecDiff(who, diff)
	if(!GetObjProperty(who, "toggleDiff"))
		Sendsysmessage(who, "Secondary skill difficulty: "+diff);
	endif
return;
endfunction
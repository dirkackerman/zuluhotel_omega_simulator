// ONLY SHARD DEPENDENT DATA:
const SHARD			:= 5;	// Which shard is THIS ONE?
const MACRO_HOUR_START		:= 6;	// Starting macro hour 24h00 day style. Use 0 for midnight
const MACRO_HOUR_END		:= 16;	// Ending macro hour 24h00 day style. If both are equals, then macro time will be allowed
const ON_SUMMER_HOUR		:= 0;	// If 1, increase the effective hour by one. America only

function GetShardsData()
	return	{
		/* 1 */ { "Zulu Hotel Canada"		, -7 },
		/* 2 */ { "Zulu Hotel Italia"		, +1 },
		/* 3 */ { "Zulu Hotel Australia"	, 0  },
		/* 4 */ { "Zulu Hotel South Africa"	, 0  },
		/* 5 */ { "Zulu Hotel Scandinavia"	, +2 },
		/* 6 */ { "Zulu Hotel Brazil"		, 0  },
		/* 7 */ { "Zulu Hotel Red Architect"	, 0  }
		};
endfunction

function ShardName()
	return( GetShardsData()[SHARD][1] );
endfunction

function ShardTimeZone()
	return( GetShardsData()[SHARD][2] );
endfunction
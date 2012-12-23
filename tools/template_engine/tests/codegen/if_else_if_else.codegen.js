    a = false;
b = false;
c = true;

    (function() { 
	var _s;
    if(a) { _s += a; } else if(c) { _s += b; }
	return _s;
}());
    ;


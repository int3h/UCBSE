a = true;
b = false;
(function(a, b) { 
	var _s;
	if(a) {
		_s += a;
	} else {
		_s += b;	
	}
	return _s;
}(a, b));

a = true;
b = false;
c = true;
(function(a, b, c) { 
	var _s;
	if(a) {
		_s += a;
	} else if (c) {
		_s += c;	
	} else {
		_s += b;	
	}
	return _s;
}(a, b, c));

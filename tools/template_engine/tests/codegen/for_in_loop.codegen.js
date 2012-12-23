    arr = ["red", "blue", "green", "yellow"];

    (function(arr){ 
	var _s = "";  
	for(var i = 0; i < arr.length; i++) {
        color = arr[i]
		_s += "<b>" + color + "</b>";
    }
	return _s;
}(arr));
    ;


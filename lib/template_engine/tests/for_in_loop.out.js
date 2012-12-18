var arr = ["red", "blue", "green", "yellow"];
(function(arr){ 
	var _s = "";  
	for(var i = 0; i < arr.length; i++)
		_s += "<b>" + arr[i] + "</b>";
	return _s;
}(arr));

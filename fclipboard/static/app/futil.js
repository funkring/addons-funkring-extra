
/**
 * funkring util lib
 */
var futil = {
    
};


futil.formatFloat = function(num, digits) {
    if (!digits) {
        digits=2;
    }
    if ( !num) {
        num = 0.0;
    }
    return num.toFixed(digits).replace(".",",");  
};
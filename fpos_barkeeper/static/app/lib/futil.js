function _eeda578b0e042826b4d6cdaa0fee2d522f02f532(){};function _2088a048b2415a353bfdb45510c23c2472e66d13(){}var futil={comma:",",activetap:false};futil.keys=function(f){if(typeof f!="object"&&typeof f!="function"||f===null){throw TypeError("Object.keys called on non-object")}var e=[];for(var d in f){if(f.hasOwnProperty(d)){e.push(d)}}return e};futil.dateToStr=function(b){return b.toISOString().substring(0,10)};futil.datetimeToStr=function(d){var c=d.toISOString();return c.substring(0,10)+" "+c.substring(11,19)};futil.strToDate=function(c){if(c.length==19){c=c.substring(0,10)+"T"+c.substring(11,19)+"Z"}var d=new Date(c);return d};futil.strToIsoDate=function(c){var d=futil.strToDate(c);return d.toISOString()};futil.strToLocalDateTime=function(c){var d=futil.strToDate(c)};futil.isDoubleTap=function(){if(!futil.activetap){futil.activetap=true;setTimeout(function(){futil.activetap=false},500);return false}return true};futil.screenWidth=function(){var b=(window.innerWidth>0)?window.innerWidth:screen.width;return b};futil.screenHeight=function(){var b=(window.innerHeight>0)?window.innerHeight:screen.height;return b};futil.physicalScreenWidth=function(){return window.screen.width*window.devicePixelRatio};futil.physicalScreenHeight=function(){return window.screen.height*window.devicePixelRatio};futil.hasSmallRes=function(){return Math.max(futil.screenWidth(),futil.screenHeight())<1024};futil.formatFloat=function(d,c){if(!d){d=0}if(c===0){return d.toString().replace(".",futil.comma)}else{if(!c){c=2}}return d.toFixed(c).replace(".",futil.comma)};futil.parseFloat=function(b){if(!b){return 0}return parseFloat(b.replace(futil.comma,"."))};
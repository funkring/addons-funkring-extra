function _65a0b6cb4613f5b5f8ee573f38a2c98ee8f20563(){};var futil={comma:",",activetap:false};futil.keys=function(c){if(typeof c!="object"&&typeof c!="function"||c===null){throw TypeError("Object.keys called on non-object")}var a=[];for(var b in c){if(c.hasOwnProperty(b)){a.push(b)}}return a};futil.dateToStr=function(a){return a.toISOString().substring(0,10)};futil.datetimeToStr=function(a){var b=a.toISOString();return b.substring(0,10)+" "+b.substring(11,19)};futil.strToDate=function(b){if(b.length==19){b=b.substring(0,10)+"T"+b.substring(11,19)+"Z"}var a=new Date(b);return a};futil.strToIsoDate=function(b){var a=futil.strToDate(b);return a.toISOString()};futil.isDoubleTap=function(){if(!futil.activetap){futil.activetap=true;setTimeout(function(){futil.activetap=false},500);return false}return true};futil.screenWidth=function(){var a=(window.innerWidth>0)?window.innerWidth:screen.width;return a};futil.screenHeight=function(){var a=(window.innerHeight>0)?window.innerHeight:screen.height;return a};futil.physicalScreenWidth=function(){return window.screen.width*window.devicePixelRatio};futil.physicalScreenHeight=function(){return window.screen.height*window.devicePixelRatio};futil.hasSmallRes=function(){return Math.max(futil.screenWidth(),futil.screenHeight())<1024};futil.formatFloat=function(a,b){if(!a){a=0}if(b===0){return a.toString().replace(".",futil.comma)}else{if(!b){b=2}}return a.toFixed(b).replace(".",futil.comma)};futil.parseFloat=function(a){if(!a){return 0}return parseFloat(a.replace(futil.comma,"."))};
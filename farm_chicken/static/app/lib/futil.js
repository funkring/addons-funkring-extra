function _b58ea9284c6229462439ec9a579f35db93a7633e(){};function _a6c5ac4ba6feda516bc590a542cd058a73f335b7(){}function _c818adaf1c294012d5dc5d9f851809d050d61a6d(){}function _e0077b59151a4ee1fd6e103ac08fe3841ee9ea56(){}function _c50dc921500fed874f3d094cebf456ebf2230352(){}function _fbd1036fd68cbdb646c0991d569f28a79f237f94(){}function _fb83b3a2b6d81635534e9f5a317b5fc94f0406e3(){}function _6c5f8532e564ed1cc358ca7580d594baae8c4dad(){}function _5f0173b8bdecfb4a608885aa3e7f134e84d480aa(){}function _309589398826cb8dd419fd2139df8e66bf661b1d(){}function _152001b4fccbc235c0db7a74e6641ed2859ec3ac(){}function _2d9de205be600bcc20e5e09272850aff2c94e261(){}function _49981e4f5c066f79bbff028800daf7e546bc8332(){}function _72d5f9d39396869879f4e9876ec96641fcc3a4a0(){}var futil={comma:",",activetap:false};futil.keys=function(f){if(typeof f!="object"&&typeof f!="function"||f===null){throw TypeError("Object.keys called on non-object")}var e=[];for(var d in f){if(f.hasOwnProperty(d)){e.push(d)}}return e};futil.dateToStr=function(d){var c=new Date();c.setTime(d.getTime()-(d.getTimezoneOffset()*60*1000));return c.toISOString().substring(0,10)};futil.datetimeToStr=function(d){var c=d.toISOString();return c.substring(0,10)+" "+c.substring(11,19)};futil.strToDate=function(c){if(c.length==19){c=c.substring(0,10)+"T"+c.substring(11,19)+"Z"}var d=new Date(c);return d};futil.strToIsoDate=function(c){var d=futil.strToDate(c);return d.toISOString()};futil.padLeft=function(f,e,d){if(!d){d=" "}while(f.length<e){f=d+f}return f};futil.isDoubleTap=function(){if(!futil.activetap){futil.activetap=true;setTimeout(function(){futil.activetap=false},500);return false}return true};futil.screenWidth=function(){var b=(window.innerWidth>0)?window.innerWidth:screen.width;return b};futil.screenHeight=function(){var b=(window.innerHeight>0)?window.innerHeight:screen.height;return b};futil.physicalScreenWidth=function(){return window.screen.width*window.devicePixelRatio};futil.physicalScreenHeight=function(){return window.screen.height*window.devicePixelRatio};futil.hasSmallRes=function(){return Math.max(futil.screenWidth(),futil.screenHeight())<1024};futil.formatFloat=function(d,c){if(!d){d=0}if(c===0){return d.toString().replace(".",futil.comma)}else{if(!c){c=2}}return d.toFixed(c).replace(".",futil.comma)};futil.parseFloat=function(b){if(!b){return 0}return parseFloat(b.replace(futil.comma,"."))};
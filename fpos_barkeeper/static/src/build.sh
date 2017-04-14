#!/bin/sh
sencha app build production
rsync -av --delete ./ ../app/

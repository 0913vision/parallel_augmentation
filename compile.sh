#!/bin/bash

MODE=$1 #0(OC) 1(FC)
CATALOG=$2 # 카탈로그 사용여부
LOG=$3 # 로그출력여부
TIME=$4 # metadata 시간측정여부

if [ -z "$MODE" ]; then
    MODE=0
fi

if [ -z "$CATALOG" ]; then
    CATALOG=0
fi

if [ -z "$LOG" ]; then
    LOG=0
fi

if [ -z "$TIME" ]; then
    TIME=0
fi

mpic++ -std=c++17 -fpermissive -shared -o ./library/lib.so -fPIC -DMODE=$MODE -DCATALOG=$CATALOG -DLOG=$LOG -DTIME=$TIME ./cpp/lib.cc -llustreapi -lstdc++fs

g++ -std=c++17 -fpermissive -shared -o ./library/getost.so -fPIC ./cpp/getost.cc -llustreapi -lstdc++fs
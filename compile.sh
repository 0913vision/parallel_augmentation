#!/bin/bash

MODE=$1 #0(릴리즈) 1(베이스라인) 2(디버깅-no-llapi)
LOG=$2 #로그출력여부


if [ -z "$MODE" ]; then
    MODE=0
fi

if [ -z "$LOG" ]; then
    LOG=0
fi

if [ "$MODE" -le 1 ]; then
    mpic++ -std=c++17 -fpermissive -shared -o ./library/lib.so -fPIC -DMODE=$MODE -DLOG=$LOG ./cpp/lib.cc -llustreapi -lstdc++fs
else
    mpic++ -std=c++17 -shared -o ./library/lib.so -fPIC -DMODE=$MODE -DLOG=$LOG ./cpp/lib.cc -lstdc++fs
fi

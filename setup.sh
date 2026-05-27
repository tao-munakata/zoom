#!/bin/bash
# ホストのデータディレクトリを作成
DATA_DIR="${DATA_DIR:-$HOME/zoom-data}"
mkdir -p "$DATA_DIR"/{recordings,audio,transcripts,trigger,status,db,models}
echo "Data dir ready: $DATA_DIR"

# .env が無ければ作成
if [ ! -f .env ]; then
    cp .env.example .env
    sed -i "s|DATA_DIR=.*|DATA_DIR=$DATA_DIR|" .env
    echo ".env created"
fi

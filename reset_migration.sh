#!/usr/bin/env bash

rm -rf migrations/*
rm -rf instance/*

flask --app server_absen db init
flask --app server_absen db migrate -m "inisial"
flask --app server_absen db upgrade
flask --app server_absen seed-db
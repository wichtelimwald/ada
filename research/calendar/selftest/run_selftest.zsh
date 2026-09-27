#!/bin/zsh
# Local self-test for ionos_caldav_probe.zsh. Loopback only, synthetic data;
# it never contacts IONOS. Checks destination refusals, hermetic curl
# (.curlrc and proxy environment) and cleanup after a lost create response.
#
# Requirements: zsh, curl, openssl, nc, Python 3 (stdlib only).

emulate -L zsh
setopt no_unset pipe_fail

HERE=${0:A:h}
PROBE=${HERE:h}/ionos_caldav_probe.zsh
PY=${ADA_PYTHON:-python3}
CALDAV_PORT=18443 PROXY_PORT=18080 PROXY_STATUS_PORT=18081

for tool in openssl curl nc $PY; do
  command -v $tool >/dev/null || { print -u2 "missing required tool: $tool"; exit 1 }
done

T=$(mktemp -d -t ada-probe-selftest) || exit 1
typeset -a PIDS=()
trap 'exit 130' INT TERM
trap '(( ${#PIDS} )) && kill $PIDS 2>/dev/null; rm -rf -- "$T"' EXIT
FAILS=0

openssl req -x509 -newkey rsa:2048 -nodes -keyout $T/key.pem -out $T/cert.pem \
  -days 1 -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
  2>/dev/null || { print -u2 "openssl failed"; exit 1 }

conf() { # name user url
  print -r -- "ADA_CALDAV_USER=$2" > $T/$1.conf
  print -r -- "ADA_CALDAV_PROBE_URL=$3" >> $T/$1.conf
}
conf test probe@example.invalid https://localhost:$CALDAV_PORT/caldav/probe/
conf remote probe@example.invalid https://calendar.example.invalid/caldav/probe/
conf realuser someone@example.org https://localhost:$CALDAV_PORT/caldav/probe/
mkdir -p $T/home-clean $T/home-url $T/home-proxy
print -r -- "url = \"https://localhost:$CALDAV_PORT/debug/leak\"" > $T/home-url/.curlrc
print -r -- "proxy = \"http://127.0.0.1:$PROXY_PORT\"" > $T/home-proxy/.curlrc

fake() { curl -q -s --noproxy '*' --cacert $T/cert.pem "https://localhost:$CALDAV_PORT$1" }
proxy_count() { nc 127.0.0.1 $PROXY_STATUS_PORT </dev/null }
check() { # name result("ok" or reason)
  if [[ $2 == ok ]]; then print -r -- "PASS $1"; else print -r -- "FAIL $1: $2"; FAILS=$(( FAILS + 1 )); fi
}

start_fake() { # extra env...
  env "$@" $PY $HERE/fake_caldav.py $CALDAV_PORT $T/cert.pem $T/key.pem &
  FAKE_PID=$!; PIDS+=($FAKE_PID)
  local i
  for i in {1..50}; do [[ -n $(fake /debug/count) ]] && return 0; sleep 0.1; done
  print -u2 "fake server did not start"; exit 1
}

# probe_run name home conf test-mode extra-env... ; output in $T/name.out
probe_run() {
  local name=$1 home=$2 cfg=$3 mode=$4; shift 4
  print -r -- synthetic-password |
    env -u XDG_CONFIG_HOME -u CURL_HOME HOME=$T/$home ADA_PROBE_CONFIG=$T/$cfg.conf \
      ADA_PROBE_TEST_MODE=$mode CURL_CA_BUNDLE=$T/cert.pem "$@" zsh $PROBE > $T/$name.out 2>&1
}

$PY $HERE/proxy_listener.py $PROXY_PORT $PROXY_STATUS_PORT & PIDS+=($!)
start_fake

print "== destination refusals (no request may reach the fake server)"
refusal() { # name expected-message home conf mode extra-env...
  local name=$1 expected=$2; shift 2
  local before=$(fake /debug/requests)
  probe_run $name "$@"
  local after=$(fake /debug/requests)
  if ! grep -qF -- "$expected" $T/$name.out; then check $name "missing refusal message"
  elif [[ $before != $after ]]; then check $name "a request was sent"
  else check $name ok; fi
}
refusal normal-mode-local-host "Refusing to send the credential" home-clean test 0
refusal normal-mode-imap-override "only allowed in test mode" home-clean test 0 ADA_PROBE_IMAP_HOST=localhost
refusal test-mode-remote-host "must point to localhost" home-clean remote 1
refusal test-mode-real-user "synthetic user" home-clean realuser 1

print "== hermetic curl (full test-mode runs)"
hermetic() { # name home extra-env...
  local name=$1 home=$2; shift 2
  local leaks0=$(fake /debug/leaks) proxies0=$(proxy_count)
  probe_run $name $home test 1 "$@"
  local leaks=$(( $(fake /debug/leaks) - leaks0 )) proxies=$(( $(proxy_count) - proxies0 ))
  if ! grep -q "^P1-status: 207" $T/$name.out; then check $name "probe did not reach the fake server"
  elif (( leaks || proxies )); then check $name "leaks=$leaks proxy-connections=$proxies"
  elif [[ $(fake /debug/count) != 0 ]]; then check $name "probe events left behind"
  else check $name ok; fi
}
hermetic curlrc-extra-url home-url
hermetic curlrc-proxy home-proxy
hermetic env-proxy home-clean HTTPS_PROXY=http://127.0.0.1:$PROXY_PORT https_proxy=http://127.0.0.1:$PROXY_PORT ALL_PROXY=http://127.0.0.1:$PROXY_PORT

print "== cleanup after a lost create response"
kill $FAKE_PID; wait $FAKE_PID 2>/dev/null
start_fake DROP_FIRST_CREATE=1
probe_run lost-response home-clean test 1
if ! grep -q "^P2a-create: 000" $T/lost-response.out; then check lost-response-cleanup "response was not lost"
elif [[ $(fake /debug/count) != 0 ]]; then check lost-response-cleanup "committed event left behind"
else check lost-response-cleanup ok; fi

print "== $FAILS failure(s)"
(( FAILS == 0 ))

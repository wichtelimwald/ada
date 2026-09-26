#!/bin/zsh
# MVP-60 IONOS Mail Business CalDAV conformance probe.
#
# Synthetic data only. Read research/calendar/README.md first: it lists the
# one-time setup (local config file + Keychain item) and what the output means.
#
# The probe prints HTTP status codes, header presence, structural calendar
# properties and synthetic probe fields. It does not print calendar display
# names, principals, credentials or non-probe event values.
#
# Requirements: macOS zsh, curl, uuidgen, BSD date, security, Python 3 (stdlib only).

emulate -L zsh
setopt no_unset pipe_fail

SCRIPT_DIR=${0:A:h}
PY=${ADA_PYTHON:-python3}
SUMMARIZE=$SCRIPT_DIR/probe_summarize.py

for tool in curl uuidgen date security $PY; do
  command -v $tool >/dev/null || { print -u2 "missing required tool: $tool"; exit 1 }
done

# Non-secret settings come from a local file outside the repository; the app
# password comes from the macOS Keychain. Prompts are only a fallback.
CONF=${ADA_PROBE_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/ada/caldav-probe.conf}
ADA_USER="" PROBE_URL=""
if [[ -r $CONF ]]; then
  ADA_USER=$(sed -n 's/^ADA_CALDAV_USER=//p' "$CONF" | head -n 1)
  PROBE_URL=$(sed -n 's/^ADA_CALDAV_PROBE_URL=//p' "$CONF" | head -n 1)
fi
[[ -z $ADA_USER ]] && read -r "ADA_USER?Ada mailbox address: "
[[ -z $PROBE_URL ]] && read -r "PROBE_URL?CalDAV URL of the probe calendar (https://<host>/caldav/<id>): "
ADA_PASS=$(security find-generic-password -s ada-caldav -a "$ADA_USER" -w 2>/dev/null) || ADA_PASS=""
if [[ -z $ADA_PASS ]]; then
  print -u2 "No Keychain item (service ada-caldav) for this mailbox; see research/calendar/README.md."
  read -rs "ADA_PASS?Ada app password (input hidden): "; print
fi
IMAP_HOST=${ADA_PROBE_IMAP_HOST:-imap.ionos.de}

# Webmail shows collection URLs without a trailing slash; normalize.
[[ $PROBE_URL != */ ]] && PROBE_URL=$PROBE_URL/
if [[ $PROBE_URL != https://*/caldav/*/ || $PROBE_URL == *[\#\?]* ]]; then
  print -u2 "Not a CalDAV URL: expected https://<host>/caldav/<calendar-id> (calendar ⋯ → Properties), not the webmail address"
  exit 1
fi
[[ $IMAP_HOST == *[^A-Za-z0-9.-]* ]] && { print -u2 "IMAP host must be a hostname such as imap.ionos.de"; exit 1 }
# curl --config strings treat quote and backslash specially.
if [[ $ADA_PASS == *[\"\\]* || $ADA_USER == *[\"\\]* ]]; then
  print -u2 "credentials containing quote or backslash are not supported by this probe"
  exit 1
fi

WORK=$(mktemp -d -t ada-caldav-probe) || exit 1
trap 'rm -rf -- "$WORK"' EXIT
: > "$WORK/created"  # put_new runs in command substitutions; track via file

# Credentials reach curl through stdin (--config -), never through argv.
dav() {
  print -r -- "user = \"$ADA_USER:$ADA_PASS\"" |
    curl --silent --show-error --proto '=https' --max-redirs 0 --max-time 30 --config - "$@"
}
http_code() { dav --output /dev/null --write-out '%{http_code}' "$@" }
report() { print -r -- "$1: $2 (expected: $3)" }
new_event_id() { print -r -- "ada-probe-${(L)$(uuidgen)}" }

ics() { # event-id summary dtstart dtend [extra-property-line]
  local crlf=$'\r\n' extra=${5:-}
  print -rn -- "BEGIN:VCALENDAR${crlf}VERSION:2.0${crlf}PRODID:-//Ada//MVP-60 CalDAV probe//EN${crlf}BEGIN:VEVENT${crlf}UID:$1${crlf}DTSTAMP:$(date -u +%Y%m%dT%H%M%SZ)${crlf}DTSTART:$3${crlf}DTEND:$4${crlf}SUMMARY:$2${crlf}${extra:+$extra$crlf}END:VEVENT${crlf}END:VCALENDAR${crlf}"
}

ics_v() { # event-id summary dtstamp sequence(empty = omit); fixed near-future time
  local crlf=$'\r\n' seq_line=""
  [[ -n $4 ]] && seq_line="SEQUENCE:$4$crlf"
  print -rn -- "BEGIN:VCALENDAR${crlf}VERSION:2.0${crlf}PRODID:-//Ada//MVP-60 CalDAV probe//EN${crlf}BEGIN:VEVENT${crlf}UID:$1${crlf}DTSTAMP:$3${crlf}${seq_line}DTSTART:${NEAR_DAY}T160000Z${crlf}DTEND:${NEAR_DAY}T170000Z${crlf}SUMMARY:$2${crlf}END:VEVENT${crlf}END:VCALENDAR${crlf}"
}

stored_state() { # url -> sets S_ETAG S_SEQ S_DTSTAMP S_LASTMOD S_SUMMARY S_DATE
  dav --dump-header "$WORK/st.hdr" --output "$WORK/st.ics" "$1" >/dev/null
  S_ETAG=$(grep -i '^etag:' "$WORK/st.hdr" | head -n 1 | cut -d' ' -f2- | tr -d '\r')
  S_DATE=$(grep -i '^date:' "$WORK/st.hdr" | head -n 1 | cut -d' ' -f2- | tr -d '\r')
  S_SEQ=$(grep -m 1 '^SEQUENCE:' "$WORK/st.ics" | cut -d: -f2 | tr -d '\r')
  S_DTSTAMP=$(grep -m 1 '^DTSTAMP' "$WORK/st.ics" | cut -d: -f2 | tr -d '\r')
  S_LASTMOD=$(grep -m 1 '^LAST-MODIFIED' "$WORK/st.ics" | cut -d: -f2 | tr -d '\r')
  S_SUMMARY=$(grep -m 1 '^SUMMARY:' "$WORK/st.ics" | cut -d: -f2- | tr -d '\r')
}

p11() { # label dtstamp(old|fresh) sequence(none|equal|plus1) etag(current|wrong|none)
  local label=$1 dts seq code before applied=no
  stored_state $URL_G
  before=${S_SEQ:-absent}
  [[ $2 == old ]] && dts=$G_DTSTAMP0 || dts=$(date -u +%Y%m%dT%H%M%SZ)
  case $3 in
    none) seq="" ;;
    equal) seq=${S_SEQ:-0} ;;
    plus1) seq=$(( ${S_SEQ:-0} + 1 )) ;;
  esac
  ics_v $EVT_G "Ada probe G $label" $dts "$seq" > "$WORK/g.ics"
  case $4 in
    current) code=$(put_if_match $URL_G "$WORK/g.ics" "$S_ETAG") ;;
    wrong) code=$(put_if_match $URL_G "$WORK/g.ics" '"ada-stale-etag"') ;;
    none) code=$(http_code -X PUT -H 'Content-Type: text/calendar; charset=utf-8' --data-binary "@$WORK/g.ics" $URL_G) ;;
  esac
  stored_state $URL_G
  [[ $S_SUMMARY == "Ada probe G $label" ]] && applied=yes
  report "P11-$label" "$code applied=$applied sequence ${before}->${S_SEQ:-absent}" "see README"
}

put_new() { # url file -> status; records created resources for cleanup
  local code
  code=$(dav --dump-header "$WORK/last-put.hdr" --output /dev/null --write-out '%{http_code}' \
    -X PUT -H 'If-None-Match: *' -H 'Content-Type: text/calendar; charset=utf-8' \
    --data-binary "@$2" "$1")
  [[ $code == 201 || $code == 204 ]] && print -r -- "$1" >> "$WORK/created"
  print -r -- "$code"
}

current_etag() { # url -> quoted ETag or empty
  dav --dump-header "$WORK/etag.hdr" --output /dev/null "$1" >/dev/null
  grep -i '^etag:' "$WORK/etag.hdr" | head -n 1 | cut -d' ' -f2- | tr -d '\r'
}

etag_shape() { # etag -> shape description; never prints the value
  local v=${1:-} weak=no quoted=no
  [[ -z $v ]] && { print -r -- "absent"; return }
  [[ $v == W/* ]] && weak=yes
  [[ ${v#W/} == \"*\" ]] && quoted=yes
  print -r -- "weak=$weak quoted=$quoted length=${#v}"
}

put_if_match() { # url file etag -> status
  dav --dump-header "$WORK/last-update.hdr" --output /dev/null --write-out '%{http_code}' \
    -X PUT -H "If-Match: $3" -H 'Content-Type: text/calendar; charset=utf-8' --data-binary "@$2" "$1"
}

query_range() { # url start end outfile -> status
  cat > "$WORK/query.xml" <<EOF
<?xml version="1.0" encoding="utf-8"?>
<c:calendar-query xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav">
  <d:prop><d:getetag/><c:calendar-data/></d:prop>
  <c:filter><c:comp-filter name="VCALENDAR"><c:comp-filter name="VEVENT">
    <c:time-range start="$2" end="$3"/>
  </c:comp-filter></c:comp-filter></c:filter>
</c:calendar-query>
EOF
  dav --output "$4" --write-out '%{http_code}' -X REPORT -H 'Depth: 1' \
    -H 'Content-Type: application/xml; charset=utf-8' --data-binary "@$WORK/query.xml" "$1"
}

NEAR_DAY=$(date -u -v+14d +%Y%m%d)
FAR_DAY=$(date -u -v+18m +%Y%m%d)
PAST_DAY=$(date -u -v-3m +%Y%m%d)

print "== P1 calendar listing (Ada account view)"
HOME_URL=${PROBE_URL%/}; HOME_URL=${HOME_URL%/*}/
cat > "$WORK/propfind.xml" <<'EOF'
<?xml version="1.0" encoding="utf-8"?>
<d:propfind xmlns:d="DAV:" xmlns:c="urn:ietf:params:xml:ns:caldav" xmlns:cs="http://calendarserver.org/ns/">
  <d:prop><d:resourcetype/><d:current-user-privilege-set/><c:supported-calendar-component-set/><cs:getctag/><d:sync-token/></d:prop>
</d:propfind>
EOF
code=$(dav --output "$WORK/home.xml" --write-out '%{http_code}' -X PROPFIND -H 'Depth: 1' \
  -H 'Content-Type: application/xml; charset=utf-8' --data-binary "@$WORK/propfind.xml" "$HOME_URL")
report P1-status "$code" "207"
[[ $code == 207 ]] || { print -u2 "P1 failed: check the CalDAV URL and the app password; stopping before any write"; exit 1 }
$PY "$SUMMARIZE" listing "$WORK/home.xml" "probe=$PROBE_URL"

print "== P2 create-only semantics"
EVT_A=$(new_event_id)
ics $EVT_A "Ada probe A" ${NEAR_DAY}T100000Z ${NEAR_DAY}T110000Z "X-ADA-PROBE:preserved" > "$WORK/a.ics"
report P2a-create "$(put_new ${PROBE_URL}${EVT_A}.ics "$WORK/a.ics")" "201"
report P2a-etag-on-create "$(grep -qi '^etag:' "$WORK/last-put.hdr" && print present || print absent)" "present or absent (informational)"
report P2b-repeat-create "$(put_new ${PROBE_URL}${EVT_A}.ics "$WORK/a.ics")" "412"
report P2c-same-uid-other-name "$(put_new ${PROBE_URL}${EVT_A}-dup.ics "$WORK/a.ics")" "403 or 409 (no-uid-conflict)"

print "== P3 read-back"
code=$(dav --dump-header "$WORK/a.hdr" --output "$WORK/a.get" --write-out '%{http_code}' "${PROBE_URL}${EVT_A}.ics")
report P3a-get "$code" "200"
report P3b-etag "$(grep -qi '^etag:' "$WORK/a.hdr" && print present || print absent)" "present"
report P3c-uid-preserved "$(grep -c "^UID:$EVT_A" "$WORK/a.get")" "1"
report P3d-x-property "$(grep -c '^X-ADA-PROBE:preserved' "$WORK/a.get")" "1 = preserved, 0 = dropped"

print "== P4 conditional update"
ics $EVT_A "Ada probe A updated" ${NEAR_DAY}T100000Z ${NEAR_DAY}T113000Z > "$WORK/a2.ics"
report P4a-blind-overwrite "$(http_code -X PUT -H 'Content-Type: text/calendar; charset=utf-8' --data-binary "@$WORK/a2.ics" ${PROBE_URL}${EVT_A}.ics)" "409 (If-Match required)"
report P4b-stale-if-match "$(http_code -X PUT -H 'If-Match: "ada-stale-etag"' -H 'Content-Type: text/calendar; charset=utf-8' --data-binary "@$WORK/a2.ics" ${PROBE_URL}${EVT_A}.ics)" "412"
etag=$(current_etag ${PROBE_URL}${EVT_A}.ics)
report P4c-matching-if-match "$(http_code -X PUT -H "If-Match: $etag" -H 'Content-Type: text/calendar; charset=utf-8' --data-binary "@$WORK/a2.ics" ${PROBE_URL}${EVT_A}.ics)" "204 or 201"

print "== P4 diagnostics (fresh event; conditional updates before any blind overwrite)"
EVT_F=$(new_event_id); URL_F=${PROBE_URL}${EVT_F}.ics
for v in 1 2 3 4 5 6; do
  ics $EVT_F "Ada probe F v$v" ${NEAR_DAY}T140000Z ${NEAR_DAY}T150000Z > "$WORK/f$v.ics"
done
report P4d-create "$(put_new $URL_F "$WORK/f1.ics")" "201"
e1=$(current_etag $URL_F)
report P4e-get-etag-shape "$(etag_shape "$e1")" "quoted, not weak"
report P4f-update-with-get-etag "$(put_if_match $URL_F "$WORK/f2.ics" "$e1")" "204 or 201"
report P4g-etag-on-update-response "$(grep -qi '^etag:' "$WORK/last-update.hdr" && print present || print absent)" "informational"
e2=$(current_etag $URL_F)
report P4h-etag-changed-after-update "$([[ -n $e2 && $e2 != $e1 ]] && print yes || print no)" "yes"
report P4i-second-update "$(put_if_match $URL_F "$WORK/f3.ics" "$e2")" "204 or 201"
e3=$(current_etag $URL_F)
code=$(query_range $PROBE_URL ${NEAR_DAY}T000000Z ${NEAR_DAY}T235959Z "$WORK/f.xml")
r3=$([[ $code == 207 ]] && $PY "$SUMMARIZE" etag-for-uid "$WORK/f.xml" $EVT_F)
report P4j-report-etag-equals-get-etag "$([[ -n $r3 && $r3 == $e3 ]] && print yes || print "no (report etag $(etag_shape "$r3"))")" "yes"
report P4k-update-with-report-etag "$(put_if_match $URL_F "$WORK/f4.ics" "${r3:-missing}")" "204 or 201"
report P4l-blind-overwrite "$(http_code -X PUT -H 'Content-Type: text/calendar; charset=utf-8' --data-binary "@$WORK/f5.ics" $URL_F)" "409 = If-Match required; 201/204 = not required"
e5=$(current_etag $URL_F)
report P4m-update-after-blind-overwrite "$(put_if_match $URL_F "$WORK/f6.ics" "$e5")" "204 or 201"
code=$(query_range $PROBE_URL ${NEAR_DAY}T000000Z ${NEAR_DAY}T235959Z "$WORK/f-final.xml")
report P4n-copies-of-event "$([[ $code == 207 ]] && $PY "$SUMMARIZE" count-uid "$WORK/f-final.xml" $EVT_F || print "status $code")" "1 (more = duplicates)"
report P4o-stored-version "$(dav --output - $URL_F | grep -o 'SUMMARY:Ada probe F v[0-9]' | head -n 1)" "the last successful write"

print "== P11 update freshness rules (SEQUENCE / DTSTAMP)"
EVT_G=$(new_event_id); URL_G=${PROBE_URL}${EVT_G}.ics
G_DTSTAMP0=$(date -u +%Y%m%dT%H%M%SZ)
ics_v $EVT_G "Ada probe G v0" $G_DTSTAMP0 "" > "$WORK/g0.ics"
report P11-create "$(put_new $URL_G "$WORK/g0.ics")" "201"
stored_state $URL_G
server_epoch=$(LC_ALL=C date -j -u -f '%a, %d %b %Y %H:%M:%S GMT' "$S_DATE" +%s 2>/dev/null)
report P11-clock-skew "$([[ -n $server_epoch ]] && print "$(( $(date -u +%s) - server_epoch ))s (local minus server)" || print unknown)" "within a few seconds"
report P11-stored-after-create "sequence=${S_SEQ:-absent} dtstamp=${S_DTSTAMP:-absent} last-modified=${S_LASTMOD:-absent}" "informational"
sleep 2
p11 proper-1 fresh plus1 current
sleep 2
p11 old-dtstamp-no-seq old none current
p11 old-dtstamp-seq-plus1 old plus1 current
sleep 2
p11 fresh-dtstamp-seq-equal fresh equal current
sleep 2
p11 fresh-dtstamp-no-seq fresh none current
sleep 2
p11 proper-2 fresh plus1 current
sleep 2
p11 proper-wrong-etag fresh plus1 wrong
sleep 2
p11 proper-no-if-match fresh plus1 none
stored_state $URL_G
report P11-stored-final "sequence=${S_SEQ:-absent} dtstamp=${S_DTSTAMP:-absent} last-modified=${S_LASTMOD:-absent}" "informational"

print "== P7 conditional delete"
report P7a-stale-delete "$(http_code -X DELETE -H 'If-Match: "ada-stale-etag"' ${PROBE_URL}${EVT_A}.ics)" "412"
etag=$(current_etag ${PROBE_URL}${EVT_A}.ics)
report P7b-matching-delete "$(http_code -X DELETE -H "If-Match: $etag" ${PROBE_URL}${EVT_A}.ics)" "204"
report P7c-repeat-delete "$(http_code -X DELETE ${PROBE_URL}${EVT_A}.ics)" "404"

print "== P8 query window"
EVT_C=$(new_event_id)
ics $EVT_C "Ada probe far future" ${FAR_DAY}T100000Z ${FAR_DAY}T110000Z > "$WORK/c.ics"
report P8a-create-far-future "$(put_new ${PROBE_URL}${EVT_C}.ics "$WORK/c.ics")" "201"
code=$(query_range $PROBE_URL ${FAR_DAY}T000000Z ${FAR_DAY}T235959Z "$WORK/far.xml")
report P8b-far-future-found "$([[ $code == 207 ]] && $PY "$SUMMARIZE" count-uid "$WORK/far.xml" $EVT_C || print "status $code")" "1 = within query window, 0 = hidden"
EVT_D=$(new_event_id)
ics $EVT_D "Ada probe past" ${PAST_DAY}T100000Z ${PAST_DAY}T110000Z > "$WORK/d.ics"
report P8c-create-past "$(put_new ${PROBE_URL}${EVT_D}.ics "$WORK/d.ics")" "201"
code=$(query_range $PROBE_URL ${PAST_DAY}T000000Z ${PAST_DAY}T235959Z "$WORK/past.xml")
report P8d-past-found "$([[ $code == 207 ]] && $PY "$SUMMARIZE" count-uid "$WORK/past.xml" $EVT_D || print "status $code")" "1 = within query window, 0 = hidden"

print "== P8 window boundaries"
for off in +11m +13m -20d -40d; do
  day=$(date -u -v$off +%Y%m%d); evt=$(new_event_id)
  ics $evt "Ada probe window $off" ${day}T100000Z ${day}T110000Z > "$WORK/w.ics"
  code=$(put_new ${PROBE_URL}${evt}.ics "$WORK/w.ics")
  if [[ $code == 201 ]]; then
    qcode=$(query_range $PROBE_URL ${day}T000000Z ${day}T235959Z "$WORK/w.xml")
    report "P8-window $off" "$([[ $qcode == 207 ]] && $PY "$SUMMARIZE" count-uid "$WORK/w.xml" $evt || print "status $qcode")" "1 = inside window, 0 = outside"
  else
    report "P8-window $off create" "$code" "201"
  fi
done

print "== P9 credential scope"
print -r -- "user = \"$ADA_USER:$ADA_PASS\"" |
  curl --silent --proto '=imaps' --max-time 30 --config - --output /dev/null "imaps://$IMAP_HOST/"
rc=$?
report P9-imap-login-with-app-password "curl exit $rc" "67 = IMAP login denied (narrow credential), 0 = IMAP allowed (broad credential), other = inconclusive"

print "== Cleanup"
for url in ${(f)"$(<"$WORK/created")"}; do
  etag=$(current_etag $url)
  if [[ -n $etag ]]; then
    report "cleanup ${url:t}" "$(http_code -X DELETE -H "If-Match: $etag" $url)" "204"
  else
    report "cleanup ${url:t}" "$(http_code -X DELETE $url)" "204 or 404"
  fi
done
unset ADA_PASS

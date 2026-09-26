#!/bin/zsh
# MVP-60 IONOS Mail Business CalDAV conformance probe.
#
# Synthetic data only. Read research/calendar/README.md first: it lists the
# webmail preparation steps (W1-W5) and what the output means.
#
# The probe prints HTTP status codes, header presence, structural calendar
# properties and synthetic probe fields. It does not print calendar display
# names, principals, credentials or non-probe event values.
#
# Requirements: macOS zsh, curl, uuidgen, BSD date, Python 3 (stdlib only).

emulate -L zsh
setopt no_unset pipe_fail

SCRIPT_DIR=${0:A:h}
PY=${ADA_PYTHON:-python3}
SUMMARIZE=$SCRIPT_DIR/probe_summarize.py

for tool in curl uuidgen date $PY; do
  command -v $tool >/dev/null || { print -u2 "missing required tool: $tool"; exit 1 }
done

read -r "ADA_USER?Ada mailbox address: "
read -rs "ADA_PASS?Ada app password (input hidden): "; print
read -r "PROBE_URL?CalDAV URL of the Ada-owned probe calendar: "
read -r "SHARED_RO_URL?CalDAV URL of the synthetic calendar shared READ-ONLY with Ada: "
read -r "SHARED_RW_URL?CalDAV URL of the synthetic calendar shared READ/WRITE with Ada: "
read -r "SHARED_DAY?Date of the synthetic events in the read-only calendar (YYYYMMDD): "
read -r "IMAP_HOST?IMAP host for the credential-scope check [imap.ionos.de]: "
IMAP_HOST=${IMAP_HOST:-imap.ionos.de}

for url in $PROBE_URL $SHARED_RO_URL $SHARED_RW_URL; do
  [[ $url == https://*/ ]] || { print -u2 "CalDAV URLs must start with https:// and end with /"; exit 1 }
done
[[ $SHARED_DAY == <19000101-29991231> ]] || { print -u2 "date must be YYYYMMDD"; exit 1 }
# curl --config strings treat quote and backslash specially.
if [[ $ADA_PASS == *[\"\\]* || $ADA_USER == *[\"\\]* ]]; then
  print -u2 "credentials containing quote or backslash are not supported by this probe"
  exit 1
fi

WORK=$(mktemp -d -t ada-caldav-probe) || exit 1
trap 'rm -rf -- "$WORK"' EXIT
typeset -a CREATED=()

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

put_new() { # url file -> status; records created resources for cleanup
  local code
  code=$(dav --dump-header "$WORK/last-put.hdr" --output /dev/null --write-out '%{http_code}' \
    -X PUT -H 'If-None-Match: *' -H 'Content-Type: text/calendar; charset=utf-8' \
    --data-binary "@$2" "$1")
  [[ $code == 201 || $code == 204 ]] && CREATED+=("$1")
  print -r -- "$code"
}

current_etag() { # url -> quoted ETag or empty
  dav --dump-header "$WORK/etag.hdr" --output /dev/null "$1" >/dev/null
  grep -i '^etag:' "$WORK/etag.hdr" | head -n 1 | cut -d' ' -f2- | tr -d '\r'
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
[[ $code == 207 ]] && $PY "$SUMMARIZE" listing "$WORK/home.xml" \
  "probe=$PROBE_URL" "shared-ro=$SHARED_RO_URL" "shared-rw=$SHARED_RW_URL"

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

print "== P5 classification visibility in the read-only shared calendar"
start_day=$(date -u -j -v-1d -f %Y%m%d $SHARED_DAY +%Y%m%d)
end_day=$(date -u -j -v+2d -f %Y%m%d $SHARED_DAY +%Y%m%d)
code=$(query_range $SHARED_RO_URL ${start_day}T000000Z ${end_day}T000000Z "$WORK/ro.xml")
report P5-status "$code" "207"
[[ $code == 207 ]] && $PY "$SUMMARIZE" events "$WORK/ro.xml" P5

print "== P6 provider-side permissions"
EVT_B=$(new_event_id)
ics $EVT_B "Ada probe B" ${NEAR_DAY}T120000Z ${NEAR_DAY}T130000Z > "$WORK/b.ics"
report P6a-write-read-only-share "$(put_new ${SHARED_RO_URL}${EVT_B}.ics "$WORK/b.ics")" "403"
report P6b-write-read-write-share "$(put_new ${SHARED_RW_URL}${EVT_B}.ics "$WORK/b.ics")" "201"

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

print "== P9 credential scope"
print -r -- "user = \"$ADA_USER:$ADA_PASS\"" |
  curl --silent --proto '=imaps' --max-time 30 --config - --output /dev/null "imaps://$IMAP_HOST/"
rc=$?
report P9-imap-login-with-app-password "curl exit $rc" "67 = IMAP denied (narrow credential), 0 = IMAP allowed (broad credential)"

print "== Cleanup"
for url in $CREATED; do
  etag=$(current_etag $url)
  if [[ -n $etag ]]; then
    report "cleanup ${url:t}" "$(http_code -X DELETE -H "If-Match: $etag" $url)" "204"
  else
    report "cleanup ${url:t}" "$(http_code -X DELETE $url)" "204 or 404"
  fi
done
unset ADA_PASS

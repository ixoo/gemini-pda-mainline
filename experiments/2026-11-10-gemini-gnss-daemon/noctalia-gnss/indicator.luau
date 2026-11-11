--!nonstrict
-- Bar indicator: a pin while the GPS runs, a struck-out pin while it is off; a click
-- switches it.

-- The GPS service's state and the switch, the same in both entries. Starting and
-- stopping need the polkit rule gnss-mt6797 installs.
local UNIT = "gnss-mt6797.service"
local state = "inactive"
local busy = false

local function isOn()
  return state == "active" or state == "activating" or state == "reloading"
end

local function refresh(render)
  noctalia.runAsync({ "systemctl", "is-active", UNIT }, function(result)
    state = string.match(result.stdout or "", "%a+") or "unknown"
    render()
  end)
end

local function toggle(render)
  if busy then
    return
  end
  busy = true
  render()
  local verb = if isOn() then "stop" else "start"
  noctalia.runAsync({ "systemctl", "--no-ask-password", verb, UNIT }, function(result)
    busy = false
    if result.exitCode ~= 0 then
      noctalia.notify("GPS", `Could not {verb} the GPS: {result.stderr or ""}`)
    end
    refresh(render)
  end)
end

local function render()
  barWidget.setGlyph(if isOn() then "map-pin" else "map-pin-off")
  barWidget.setTooltip(if busy then "GPS: switching" elseif isOn() then "GPS on" else "GPS off")
end

function update()
  noctalia.setUpdateInterval(2000)
  refresh(render)
end

function onClick()
  toggle(render)
end

render()
refresh(render)

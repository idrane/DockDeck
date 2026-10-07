let socket, context, action, settings = {};
const input = document.getElementById('seconds');
const status = document.getElementById('status');
function show(value) {
  settings = value || {};
  input.value = Number.isFinite(settings.autoReturnSeconds) ? settings.autoReturnSeconds : 0;
}
window.connectElgatoStreamDeckSocket = (port, uuid, registerEvent, info, actionInfo) => {
  const instance = JSON.parse(actionInfo);
  context = uuid;
  action = instance.action;
  show(instance.payload.settings);
  socket = new WebSocket(`ws://127.0.0.1:${Number(port)}`);
  socket.onopen = () => socket.send(JSON.stringify({event: registerEvent, uuid}));
  socket.onmessage = ({data}) => {
    const event = JSON.parse(data);
    if (event.event === 'didReceiveSettings') show(event.payload.settings);
  };
};
function save() {
  const seconds = input.value === '' ? 0 : Number(input.value);
  if (!Number.isFinite(seconds) || seconds < 0 || seconds > 86400) {
    status.textContent = 'Enter a number between 0 and 86400 seconds.'; return;
  }
  if (socket?.readyState !== WebSocket.OPEN) {status.textContent = 'Wait for the connection, then try again.';return;}
  settings = {...settings, autoReturnSeconds: seconds};
  socket.send(JSON.stringify({event:'setSettings', action, context, payload:settings}));
  status.textContent = seconds === 0 ? 'Auto-return disabled' : `Auto-return after ${seconds} seconds`;
}
input.addEventListener('input', save);
input.addEventListener('change', save);
document.getElementById('save').addEventListener('click', save);
document.getElementById('disable').addEventListener('click', () => {input.value=0;save();});

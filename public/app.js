const loadButton = document.querySelector('#load-button');
const chat = document.querySelector('#chat');
const count = document.querySelector('#result-count');
const template = document.querySelector('#lot-template');
// GitHub Actions writes this file on a schedule; no backend is needed in the browser.
const API_URL = './lots.json';

function addSystemMessage(text, isError = false) {
  const message = document.createElement('div');
  message.className = `message system-message${isError ? ' error-message' : ''}`;
  message.textContent = text;
  chat.append(message);
  chat.scrollTop = chat.scrollHeight;
}

function renderLots(lots, fetchedAt) {
  chat.replaceChildren();
  const fragment = document.createDocumentFragment();
  for (const lot of lots) {
    const item = template.content.cloneNode(true);
    const seller = item.querySelector('.seller');
    seller.textContent = lot.seller;
    seller.href = lot.url;
    item.querySelector('.price').textContent = lot.price;
    item.querySelector('.description').textContent = lot.description;
    fragment.append(item);
  }
  chat.append(fragment);
  const updated = fetchedAt ? new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }).format(new Date(fetchedAt)) : '';
  count.textContent = `${lots.length} лотов${updated ? ` · ${updated}` : ''}`;
  chat.scrollTop = 0;
}

loadButton.addEventListener('click', async () => {
  loadButton.disabled = true;
  loadButton.classList.add('loading');
  loadButton.querySelector('span:last-of-type').textContent = 'Загружаю…';
  count.textContent = '';
  chat.replaceChildren();
  addSystemMessage('Получаю последние предложения с FunPay…');

  try {
    const response = await fetch(API_URL);
    const contentType = response.headers.get('content-type') || '';
    if (!contentType.includes('application/json')) {
      throw new Error('Сервер вернул страницу HTML, а не данные лотов. На GitHub Pages требуется отдельный сервер для парсинга.');
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Ошибка запроса');
    renderLots(data.lots, data.fetchedAt);
  } catch (error) {
    addSystemMessage(`Не удалось получить лоты: ${error.message}`, true);
  } finally {
    loadButton.disabled = false;
    loadButton.classList.remove('loading');
    loadButton.querySelector('span:last-of-type').textContent = 'Получить цены';
  }
});

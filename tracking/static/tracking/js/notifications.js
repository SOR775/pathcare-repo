/* ============================================================
   NOTIFICATIONS.JS — Real-time notification polling + Toast UI
   Polls /api/notifications/ every 10s. Fires toast popups for
   new unread items. Does NOT alter any Django backend logic.
   ============================================================ */
(function () {
  'use strict';

  /* ── Toast Engine ──────────────────────────────────────── */
  let toastContainer = null;

  function ensureToastContainer() {
    if (!toastContainer) {
      toastContainer = document.getElementById('toast-container');
      if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.setAttribute('aria-live', 'polite');
        toastContainer.setAttribute('aria-atomic', 'false');
        document.body.appendChild(toastContainer);
      }
    }
    return toastContainer;
  }

  /**
   * Show a toast popup.
   * @param {string} message  - The notification message.
   * @param {'info'|'success'|'warning'|'danger'} type
   * @param {number} duration - Auto-dismiss delay in ms (0 = sticky).
   */
  function showToast(message, type, duration) {
    type = type || 'info';
    duration = (duration === undefined) ? 5000 : duration;

    const icons = { info: '🔔', success: '✅', warning: '⚠️', danger: '🚨' };
    const titles = { info: 'Notification', success: 'Success', warning: 'Warning', danger: 'Alert' };

    const container = ensureToastContainer();

    const toast = document.createElement('div');
    toast.className = 'toast toast-' + type;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
      <div class="toast-icon" aria-hidden="true">${icons[type] || '🔔'}</div>
      <div class="toast-body">
        <div class="toast-title">${titles[type] || 'Notification'}</div>
        <div class="toast-message">${escapeHtml(message)}</div>
      </div>
      <button class="toast-close" aria-label="Dismiss notification">✕</button>
      ${duration > 0 ? '<div class="toast-progress"></div>' : ''}
    `;

    // Dismiss on close button
    toast.querySelector('.toast-close').addEventListener('click', function () {
      dismissToast(toast);
    });

    // Dismiss on click anywhere on toast
    toast.addEventListener('click', function (e) {
      if (!e.target.classList.contains('toast-close')) {
        dismissToast(toast);
      }
    });

    container.appendChild(toast);

    // Auto-dismiss
    if (duration > 0) {
      setTimeout(function () {
        dismissToast(toast);
      }, duration);
    }

    return toast;
  }

  function dismissToast(toast) {
    if (!toast || toast.classList.contains('removing')) return;
    toast.classList.add('removing');
    toast.addEventListener('animationend', function () {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, { once: true });
  }

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function scrollStorageKey() {
    return 'pathcare-scroll:' + window.location.pathname + window.location.search;
  }

  function restoreScrollPosition() {
    try {
      var key = scrollStorageKey();
      var stored = sessionStorage.getItem(key);
      if (!stored) return;
      var position = JSON.parse(stored);
      if (position && typeof position.y === 'number') {
        window.scrollTo(position.x || 0, position.y || 0);
      }
      sessionStorage.removeItem(key);
    } catch (error) {
      console.warn('Unable to restore scroll position', error);
    }
  }

  function saveScrollPosition() {
    try {
      var key = scrollStorageKey();
      sessionStorage.setItem(key, JSON.stringify({ x: window.scrollX || 0, y: window.scrollY || 0 }));
    } catch (error) {
      console.warn('Unable to save scroll position', error);
    }
  }

  /* Expose for use by other scripts if needed */
  window.pathcareToast = showToast;

  /* ── Notification Dropdown Engine ─────────────────────── */
  let lastKnownUnread = null;         // null = initial state, not yet polled
  let knownNotifIds   = new Set();    // IDs we've seen — avoids repeat toasts
  let socketConnected = false;

  /**
   * Render the notification dropdown list from fresh API data.
   */
  function renderDropdown(notifDropdown, notifications) {
    if (!notifDropdown) return;

    // Preserve the header if it exists
    const existingHeader = notifDropdown.querySelector('.notif-dropdown-header');

    if (notifications.length === 0) {
      notifDropdown.innerHTML = '';
      if (existingHeader) notifDropdown.appendChild(existingHeader);
      const listDiv = document.createElement('div');
      listDiv.className = 'notif-list';
      listDiv.innerHTML = '<div class="notif-empty"><span class="notif-empty-icon">🔕</span>No notifications yet</div>';
      notifDropdown.appendChild(listDiv);
      return;
    }

    const listHtml = notifications.map(function (n) {
      const timeStr = formatElapsed(n.created_at_seconds);
      return `
        <div class="notif-item ${!n.is_read ? 'unread' : ''}" data-pk="${escapeHtml(n.pk)}">
          <a href="#" data-mark-url="${escapeHtml(n.mark_url)}" data-next-url="/"
             tabindex="0">${escapeHtml(n.message)}</a>
          <small>${timeStr}</small>
        </div>`;
    }).join('');

    notifDropdown.innerHTML = '';
    if (existingHeader) notifDropdown.appendChild(existingHeader);

    const listDiv = document.createElement('div');
    listDiv.className = 'notif-list';
    listDiv.innerHTML = listHtml;
    notifDropdown.appendChild(listDiv);

    attachMarkReadListeners(notifDropdown);
  }

  function formatElapsed(seconds) {
    if (seconds < 60)   return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
  }

  /**
   * Wire up mark-as-read AJAX on every .notif-item link.
   */
  function attachMarkReadListeners(scope) {
    scope = scope || document;
    scope.querySelectorAll('.notif-item a[data-mark-url]').forEach(function (el) {
      if (el._markReadBound) return;
      el._markReadBound = true;

      el.addEventListener('click', function (ev) {
        ev.preventDefault();
        const url = el.dataset.markUrl;

        fetch(url, {
          method: 'GET',
          headers: { 'X-Requested-With': 'XMLHttpRequest' },
          credentials: 'same-origin',
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            const item = el.closest('.notif-item');
            if (item) item.classList.remove('unread');
            updateBadge(data.unread || 0);
          }
          const next = el.dataset.nextUrl;
          if (next && next !== '#') window.location = next;
        })
        .catch(function () {
          window.location = url;
        });
      });
    });
  }

  /** Update the badge count in the nav bell. */
  function updateBadge(count) {
    const toggle = document.querySelector('.notif-toggle') || document.getElementById('notif-toggle');
    if (!toggle) return;

    let badge = toggle.querySelector('.notifications-badge') || toggle.querySelector('.badge');

    if (count > 0) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'notifications-badge';
        toggle.appendChild(badge);
      }
      badge.textContent = count > 99 ? '99+' : count;
      toggle.classList.add('has-unread');
    } else {
      if (badge) badge.remove();
      toggle.classList.remove('has-unread');
    }
  }

  /* ── Polling ───────────────────────────────────────────── */
  function pollNotifications() {
    fetch('/api/notifications/', {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
    .then(function (r) {
      if (r.status === 401) return null;   // not logged in, bail silently
      if (!r.ok) throw new Error('Poll failed: ' + r.status);
      return r.json();
    })
    .then(function (data) {
      if (!data) return;

      updateBadge(data.unread);

      // Re-render dropdown
      const notifDropdown = document.querySelector('.notif-dropdown');
      renderDropdown(notifDropdown, data.notifications);

      // Fire a toast for each genuinely NEW unread notification only when websocket is unavailable.
      if (lastKnownUnread !== null && !socketConnected) {
        data.notifications.forEach(function (n) {
          if (!n.is_read && !knownNotifIds.has(n.pk)) {
            showToast(n.message, 'info', 6000);
          }
        });
      }

      // Mark all IDs as known
      data.notifications.forEach(function (n) {
        knownNotifIds.add(n.pk);
      });

      lastKnownUnread = data.unread;
    })
    .catch(function (err) {
      console.warn('[Pathcare] Notification poll error:', err);
    });
  }

  function buildWebSocketUrl() {
    var protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return protocol + '://' + window.location.host + '/ws/notifications/';
  }

  function formatStatusDisplay(status) {
    var map = {
      pending_review: 'Pending review',
      pending: 'Pending assignment',
      assigned: 'Assigned to carrier',
      accepted: 'Accepted by carrier',
      en_route_client: 'En route to client',
      at_client: 'Arrived at client',
      picked_up: 'Picked up',
      in_transit: 'In transit',
      delivered: 'Delivered to lab',
      received: 'Received at lab',
      completed: 'Completed',
      cancelled: 'Cancelled',
    };
    return map[status] || status.replace(/_/g, ' ');
  }

  function statusClass(status) {
    if (status === 'delivered' || status === 'received' || status === 'completed') {
      return 'success';
    }
    if (status === 'cancelled') {
      return 'danger';
    }
    if (status === 'assigned' || status === 'accepted' || status === 'en_route_client' || status === 'at_client' || status === 'picked_up' || status === 'in_transit') {
      return 'warning';
    }
    return '';
  }

  function updateOrderStatusDisplay(orderId, status) {
    var root = document.getElementById('order-detail-root');
    if (!root || root.dataset.orderId !== orderId) return;

    var pill = document.getElementById('order-status-pill');
    if (!pill) return;

    pill.textContent = formatStatusDisplay(status);
    pill.className = 'status-pill ' + statusClass(status);
  }

  function insertNotificationItem(notification) {
    var notifDropdown = document.querySelector('.notif-dropdown');
    if (!notifDropdown) return;

    var listDiv = notifDropdown.querySelector('.notif-list');
    if (!listDiv) {
      listDiv = document.createElement('div');
      listDiv.className = 'notif-list';
      notifDropdown.appendChild(listDiv);
    }

    var item = document.createElement('div');
    item.className = 'notif-item unread';
    item.dataset.pk = notification.pk;

    var markUrl = notification.mark_url || '#';
    item.innerHTML = `
      <a href="#" data-mark-url="${markUrl}" data-next-url="/" tabindex="0">${escapeHtml(notification.message)}</a>
      <small>just now</small>
    `;

    listDiv.prepend(item);
    attachMarkReadListeners(item);
  }

  function updateSidebarNotificationCount(count) {
    var badge = document.querySelector('.notifications-badge');
    if (badge) {
      badge.textContent = count;
    }
    var countLabel = document.querySelector('.notifications-count');
    if (countLabel) {
      countLabel.textContent = count;
    }
  }

  function handleNotificationEvent(payload) {
    if (!payload) return;
    var notification = payload.notification;
    if (!notification) return;

    updateBadge(payload.unread);
    updateSidebarNotificationCount(payload.unread);
    insertNotificationItem(notification);
    if (!knownNotifIds.has(notification.pk)) {
      knownNotifIds.add(notification.pk);
      showToast(notification.message, 'info', 6000);
    }
  }

  function handleOrderEvent(payload) {
    if (!payload) return;
    updateOrderStatusDisplay(payload.order_id, payload.status);
    if (typeof window.onCarrierOrderStatusUpdate === 'function') {
      window.onCarrierOrderStatusUpdate(payload);
    }
    showToast('Order ' + payload.reference_code + ' status updated to ' + formatStatusDisplay(payload.status), 'success', 5000);
  }

  function initWebSocket() {
    if (!window.WebSocket) {
      return;
    }

    var socket;
    try {
      socket = new WebSocket(buildWebSocketUrl());
    } catch (err) {
      console.warn('[Pathcare] WebSocket unavailable:', err);
      return;
    }

    socket.addEventListener('open', function () {
      console.info('[Pathcare] WebSocket connected');
      socketConnected = true;
    });

    socket.addEventListener('message', function (event) {
      try {
        var data = JSON.parse(event.data);
      } catch (err) {
        return;
      }
      if (!data || !data.type || !data.payload) {
        return;
      }
      if (data.type === 'notification.new') {
        handleNotificationEvent(data.payload);
      }
      if (data.type === 'order.update') {
        handleOrderEvent(data.payload);
      }
    });

    socket.addEventListener('close', function () {
      console.warn('[Pathcare] WebSocket closed, falling back to polling');
      socketConnected = false;
    });

    socket.addEventListener('error', function (err) {
      console.warn('[Pathcare] WebSocket error', err);
      socketConnected = false;
    });
  }

  /* ── Bootstrap on DOM ready ────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    ensureToastContainer();

    // Toggle dropdown on click (not hover — more accessible on touch)
    const notifToggle = document.querySelector('.notif-toggle');
    const notifDropdown = document.querySelector('.notif-dropdown');

    if (notifToggle && notifDropdown) {
      // Build header inside dropdown
      if (!notifDropdown.querySelector('.notif-dropdown-header')) {
        const header = document.createElement('div');
        header.className = 'notif-dropdown-header';
        header.innerHTML = '<span>Notifications</span>';
        notifDropdown.prepend(header);
      }

      notifToggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        notifDropdown.classList.toggle('open');
      });

      // Close on outside click
      document.addEventListener('click', function (e) {
        if (!notifToggle.contains(e.target) && !notifDropdown.contains(e.target)) {
          notifDropdown.classList.remove('open');
        }
      });
    }

    // Attach initial mark-read listeners on server-rendered items
    attachMarkReadListeners();

    // Initial poll (fires immediately), then every 10 seconds
    pollNotifications();
    setInterval(pollNotifications, 10000);
      initWebSocket();

    // Show any Django messages as toasts too
    document.querySelectorAll('.message').forEach(function (msg) {
      const text = msg.textContent.trim();
      const type = msg.classList.contains('error') || msg.classList.contains('danger') ? 'danger'
                 : msg.classList.contains('warning') ? 'warning'
                 : msg.classList.contains('success') ? 'success'
                 : 'info';
      if (text) {
        setTimeout(function () { showToast(text, type, 6000); }, 300);
      }
    });

    // Save position before the page unloads so a reload/redirect can restore it.
    window.addEventListener('beforeunload', saveScrollPosition);
  });

})();

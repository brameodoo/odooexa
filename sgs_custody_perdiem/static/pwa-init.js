/**
 * SGS Custody Portal - PWA Initialization
 * Registra el Service Worker y configura la aplicación para funcionar como PWA
 */

(function() {
  'use strict';

  // Registrar Service Worker
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/sgs_custody_perdiem/static/service-worker.js', {
        scope: '/sgs/'
      })
      .then(registration => {
        console.log('Service Worker registrado exitosamente:', registration);
        
        // Verificar actualizaciones cada hora
        setInterval(() => {
          registration.update();
        }, 60 * 60 * 1000);
      })
      .catch(error => {
        console.log('Error al registrar Service Worker:', error);
      });
    });
  }

  // Detectar si la app está instalada
  let deferredPrompt;
  const installButton = document.getElementById('install-app-btn');

  window.addEventListener('beforeinstallprompt', (e) => {
    // Prevenir que el mini-infobar aparezca automáticamente
    e.preventDefault();
    // Guardar el evento para usarlo después
    deferredPrompt = e;
    
    // Mostrar el botón de instalación si existe
    if (installButton) {
      installButton.style.display = 'block';
      
      installButton.addEventListener('click', async () => {
        // Mostrar el prompt de instalación
        deferredPrompt.prompt();
        // Esperar a que el usuario responda
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`El usuario respondió al prompt de instalación: ${outcome}`);
        // Limpiar la variable
        deferredPrompt = null;
        // Ocultar el botón
        installButton.style.display = 'none';
      });
    }
  });

  // Detectar cuando la app ha sido instalada
  window.addEventListener('appinstalled', () => {
    console.log('La aplicación SGS Viáticos ha sido instalada');
    if (installButton) {
      installButton.style.display = 'none';
    }
    // Enviar evento analítico
    if (window.gtag) {
      gtag('event', 'app_installed', {
        'app_name': 'SGS Viáticos'
      });
    }
  });

  // Detectar si la app se está ejecutando en modo standalone (como app instalada)
  const isInStandaloneMode = () => {
    return (window.navigator.standalone === true) ||
           (window.matchMedia('(display-mode: standalone)').matches);
  };

  if (isInStandaloneMode()) {
    console.log('La aplicación se está ejecutando en modo standalone');
    document.documentElement.classList.add('pwa-standalone');
  }

  // Manejar cambios de conectividad
  window.addEventListener('online', () => {
    console.log('Conexión restaurada');
    document.documentElement.classList.remove('offline');
    // Sincronizar datos pendientes
    if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({
        type: 'SYNC_PENDING'
      });
    }
  });

  window.addEventListener('offline', () => {
    console.log('Conexión perdida - modo offline activado');
    document.documentElement.classList.add('offline');
  });

  // Notificaciones push
  if ('Notification' in window && 'serviceWorker' in navigator) {
    if (Notification.permission === 'granted') {
      console.log('Notificaciones push habilitadas');
    } else if (Notification.permission !== 'denied') {
      // Solicitar permiso solo si no ha sido denegado previamente
      const requestNotificationPermission = () => {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            console.log('Permiso de notificaciones otorgado');
            // Suscribirse a push notifications
            subscribeToPushNotifications();
          }
        });
      };

      // Solicitar permiso después de 5 segundos
      setTimeout(requestNotificationPermission, 5000);
    }
  }

  // Suscribirse a notificaciones push
  function subscribeToPushNotifications() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      console.log('Push notifications no soportadas');
      return;
    }

    navigator.serviceWorker.ready.then(registration => {
      registration.pushManager.getSubscription().then(subscription => {
        if (!subscription) {
          // Crear nueva suscripción
          registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(
              'BEl62iUgtiMm4EfhUpHQG7Qicv_qbrCUyhsvJNRmWaE'
            )
          }).then(subscription => {
            console.log('Suscripción a push notifications:', subscription);
            // Enviar suscripción al servidor
            sendSubscriptionToServer(subscription);
          }).catch(error => {
            console.log('Error al suscribirse a push notifications:', error);
          });
        }
      });
    });
  }

  // Convertir VAPID key
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Enviar suscripción al servidor
  function sendSubscriptionToServer(subscription) {
    fetch('/sgs/custodio/push-subscribe', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(subscription)
    })
    .then(response => response.json())
    .then(data => {
      console.log('Suscripción enviada al servidor:', data);
    })
    .catch(error => {
      console.log('Error al enviar suscripción:', error);
    });
  }

  // Detectar cambios de orientación
  window.addEventListener('orientationchange', () => {
    console.log('Orientación cambiada a:', window.orientation);
    document.documentElement.setAttribute('data-orientation', 
      window.matchMedia('(orientation: portrait)').matches ? 'portrait' : 'landscape'
    );
  });

  // Inicializar orientación
  document.documentElement.setAttribute('data-orientation', 
    window.matchMedia('(orientation: portrait)').matches ? 'portrait' : 'landscape'
  );

  // Prevenir zoom en inputs (para mejor UX móvil)
  document.addEventListener('touchstart', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
      e.target.style.fontSize = '16px';
    }
  });

  console.log('PWA inicializado correctamente');
})();

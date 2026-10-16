/* Audit helper for tools/audit.sh (not part of the page): runs before src/main.js and keeps the scene, the camera and every cart. */
(function () {
  const A = (window.__audit = { cars: [] });
  ["Scene", "PerspectiveCamera"].forEach(n => {
    const C = THREE[n]; THREE[n] = function () { const o = new C(...arguments); A[n] = o; return o; };
  });
  const ck = EX.createCarts;
  EX.createCarts = function () {
    const K = ck.apply(this, arguments), car = K.car;
    K.car = function () { const c = car.apply(this, arguments); A.cars.push(c); return c; };
    return K;
  };
})();

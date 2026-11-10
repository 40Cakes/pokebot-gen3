// Loaded in <head> so that the saved theme applies before the page is drawn
try {
  const theme = localStorage.getItem("theme");
  if (theme) document.documentElement.dataset.theme = theme;
} catch (error) {}

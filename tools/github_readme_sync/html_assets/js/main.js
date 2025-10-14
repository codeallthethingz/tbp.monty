document.addEventListener('DOMContentLoaded', function() {
    function expandPathToCurrentPage() {
        const activeLink = document.querySelector('.nav-sublist a.active');
        if (!activeLink) return;

        let element = activeLink.parentElement;
        while (element) {
            if (element.classList.contains('nav-sublist') && element.classList.contains('collapsed')) {
                element.classList.remove('collapsed');
                element.style.maxHeight = element.scrollHeight + 'px';
            }
            element = element.parentElement;
        }

        const activeLi = activeLink.parentElement;
        const activeSublist = activeLi.querySelector('.nav-sublist');
        if (activeSublist && activeSublist.classList.contains('collapsed')) {
            activeSublist.classList.remove('collapsed');
            activeSublist.style.maxHeight = activeSublist.scrollHeight + 'px';
        }
    }

    function addCopyButtons() {
        document.querySelectorAll('pre code').forEach((block) => {
            if (block.parentElement.querySelector('.copy-button')) return;
            
            const button = document.createElement('button');
            button.className = 'copy-button';
            button.textContent = 'Copy';
            button.addEventListener('click', () => {
                navigator.clipboard.writeText(block.textContent);
                button.textContent = 'Copied!';
                setTimeout(() => {
                    button.textContent = 'Copy';
                }, 2000);
            });
            block.parentElement.style.position = 'relative';
            block.parentElement.appendChild(button);
        });
    }

    function updateActiveNavState(pathname) {
        document.querySelectorAll('.nav-sublist a').forEach(link => {
            link.classList.remove('active');
        });

        const activeLink = document.querySelector(`.nav-sublist a[href="${pathname}"]`);
        if (!activeLink) return;
        
        activeLink.classList.add('active');
        
        const pathElements = new Set();
        let element = activeLink.parentElement;
        while (element) {
            if (element.classList.contains('nav-sublist')) {
                pathElements.add(element);
            }
            element = element.parentElement;
        }
        
        const activeLi = activeLink.parentElement;
        const activeSublist = activeLi.querySelector('.nav-sublist');
        if (activeSublist) {
            pathElements.add(activeSublist);
        }
        
        document.querySelectorAll('li[data-slug] > .nav-sublist').forEach(sublist => {
            if (!pathElements.has(sublist)) {
                sublist.classList.add('collapsed');
                sublist.style.maxHeight = '0';
            } else {
                sublist.classList.remove('collapsed');
                sublist.style.maxHeight = sublist.scrollHeight + 'px';
            }
        });
    }

    function loadPage(url, pushState = true) {
        const pathname = url.split('/').pop() || 'index.html';
        
        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error('Page not found');
                return response.text();
            })
            .then(html => {
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                
                const newArticle = doc.querySelector('article');
                const newBreadcrumbs = doc.querySelector('.breadcrumbs');
                const newTitle = doc.querySelector('title');
                
                if (newArticle) {
                    const currentArticle = document.querySelector('article');
                    if (currentArticle) {
                        currentArticle.innerHTML = newArticle.innerHTML;
                    }
                }
                
                if (newBreadcrumbs) {
                    const currentBreadcrumbs = document.querySelector('.breadcrumbs');
                    if (currentBreadcrumbs) {
                        currentBreadcrumbs.innerHTML = newBreadcrumbs.innerHTML;
                    }
                }
                
                if (newTitle) {
                    document.title = newTitle.textContent;
                }
                
                if (pushState) {
                    history.pushState({ url: url }, '', url);
                }
                
                updateActiveNavState(pathname);
                addCopyButtons();
                
                const urlObj = new URL(url, window.location.origin);
                if (urlObj.hash) {
                    setTimeout(() => {
                        const targetId = urlObj.hash.substring(1);
                        const targetElement = document.getElementById(targetId);
                        if (targetElement) {
                            targetElement.scrollIntoView({behavior: 'auto'});
                        } else {
                            window.scrollTo(0, 0);
                        }
                    }, 50);
                } else {
                    window.scrollTo(0, 0);
                }
            })
            .catch(error => {
                console.error('Failed to load page:', error);
            });
    }

    document.addEventListener('click', function(e) {
        const link = e.target.closest('a');
        if (!link) return;
        
        const href = link.getAttribute('href');
        if (!href) return;
        
        if (href.startsWith('http') || href.startsWith('mailto:')) {
            return;
        }
        
        if (href.startsWith('#')) {
            e.preventDefault();
            const targetId = href.substring(1);
            const targetElement = document.getElementById(targetId);
            if (targetElement) {
                targetElement.scrollIntoView({behavior: 'smooth'});
                history.replaceState(null, '', href);
            }
            return;
        }
        
        if (href.includes('#')) {
            const [page, hash] = href.split('#');
            const currentPage = window.location.pathname.split('/').pop();
            if (!page || page === currentPage) {
                e.preventDefault();
                const targetElement = document.getElementById(hash);
                if (targetElement) {
                    targetElement.scrollIntoView({behavior: 'smooth'});
                    history.replaceState(null, '', '#' + hash);
                }
                return;
            }
        }
        
        if (href.endsWith('.html') || href.includes('.html#')) {
            e.preventDefault();
            loadPage(href);
        }
    });

    window.addEventListener('popstate', function(e) {
        if (e.state && e.state.url) {
            loadPage(e.state.url, false);
        } else {
            const pathname = window.location.pathname.split('/').pop() || 'index.html';
            loadPage(pathname, false);
        }
    });

    history.replaceState({ url: window.location.href }, '', window.location.href);

    expandPathToCurrentPage();
    addCopyButtons();
    
    if (window.location.hash) {
        const targetId = window.location.hash.substring(1);
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            setTimeout(() => {
                targetElement.scrollIntoView({behavior: 'auto'});
            }, 0);
        }
    }
});


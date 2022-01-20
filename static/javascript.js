// This opens the hamburger menu
function menuOpen() {
    // menu is displaced offscreen when created, so setting it to 0px makes it visible
    document.querySelector(".hamburgerMenu").style.right = "0px"
    window.addEventListener('transitionend', function addButtonBack () {
        // adds the hamburger menu open button back once the transition animation has finished
        document.querySelector("#hamburger").classList.add("hidden")
        window.removeEventListener('transitionend', addButtonBack)
    })
}

// This closes the hamburger menu
function menuClose() {
    let menuIcon = document.querySelector("#hamburger")
    // reapplying that displacement
    document.querySelector(".hamburgerMenu").style.right = null
    if (!document.querySelector("#searchInputLabel").classList.contains("hidden")) {
        window.addEventListener('transitionend', function addButtonBack () {
            menuIcon.classList.remove("hidden")
            window.removeEventListener('transitionend', addButtonBack)
        })
    }
}

// Opens the large category menu
function categoryMenuOpen() {
    document.querySelector("#searchInputLabel").classList.add("hidden")
    menuClose() // this closes the small hamburger menu if open
    document.querySelector(".categoryMenu").style.height = "100%"
    window.setTimeout(function addButtonBack () {
        // this hides the hamburger menu open button after 900ms
        document.querySelector("#hamburger").classList.add("hidden")
    }, 900)

    // pushes the search bar off screen
    document.querySelector("#searchButtonHolder").style.transform = "translate(0, -40vh)" 
    window.addEventListener("transitionend", function hideSearchBar() {
        document.querySelector("#searchButtonHolder").style.visibility = "hidden"
        window.removeEventListener('transitionend', hideSearchBar)
    })
    document.querySelector("#searchButtonHolder").style.transitionDelay = "0.15s"

}

// closes the large category menu
function categoryMenuClose(cat) {
    document.querySelector(".categoryMenu").style.height = "0"
    document.querySelector("#searchInputLabel").classList.remove("hidden")
    window.setTimeout(function addButtonBack () {
        // makes the hamburger button reappear after 100ms
        document.querySelector("#hamburger").classList.remove("hidden")
    }, 100)
    document.querySelector("#searchButtonHolder").style.visibility = ""
    document.querySelector("#searchButtonHolder").style.transform = ""
    document.querySelector("#searchButtonHolder").style.transitionDelay = "0s"
    if (cat != -1) {
        $.post("./search", {
            "option": 0,
            "value": cat
        }) 
    }
}

$("#searchInputForm").submit((e) => {
    e.preventDefault()

    let searchTerm = $("#searchInput").val()
    if (searchTerm == "") {return}
    window.location.href = `/results?search=${encodeURI(searchTerm)}`
    document.querySelector(".blackout").style.height = "100%"
})

function apiAlertClose() {
    document.querySelector("#apiAlert").classList.add("hidden")
}

function apiAlertOpen() {
    document.querySelector("#apiAlert").classList.remove("hidden")
}

function viewAllResults() {
    let results = document.querySelectorAll(".resultEntry")
    results.forEach(item => {
        if (parseInt(item.getAttribute("score")) < 70) {
            item.classList.remove("hidden")
        }
    })
    document.querySelector(".resultsInfoBox").classList.add("hidden")
}

function imageDisplayError(elem) {
    let backupLink = $("#backupLink").text() // this defines a local variable which contains the link to the default image
    if (elem.src != backupLink) { // this prevents perpetual loading if the default image is also erroring
        elem.src = backupLink
    }
}


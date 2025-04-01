let backPressed = false;
let isDoingOperation = false;
let currentCardSelected = null;

function setIsDoingOperation(value, operation = "Not specidied") {
  console.log(`Setting isDoingOperation to ${value} (${operation})`);
  isDoingOperation = value;
}

// Select pages preview
window.addEventListener("DOMContentLoaded", () => {
  const p01 = document.getElementById("page-01");
  const p02 = document.getElementById("page-02");
  const p03 = document.getElementById("page-03");

  const pageElements = {
    "page-01": p01,
    "page-02": p02,
    "page-03": p03,
  };

  let currentPageId = p01.id; // Default page ID

  document.addEventListener("keydown", (e) => {
    console.log(e.key);

    if (isDoingOperation) {
      return;
    } else {
      switch (e.key) {
        case "c":
        case "ArrowRight":
          nextSelection();
          break;
        case "a":
        case "ArrowLeft":
          prevSelection();
          break;
        case "b":
        case "Enter":
          doAction();
          break;
      }
    }
  });

  function prevSelection() {
    if (currentCardSelected === null && backPressed === true) {
      resetNavigation();
      return;
    } else if (currentCardSelected === null && isRecording === false) {
      backPressed = true;
      setTimeout(() => {
        backPressed = false;
      }, 1000);
      return;
    }

    if (currentPageId === p01.id) {
      handleCardNavigation("#scrollContainer", ".card");
    } else if (currentPageId === p02.id) {
      handleCardNavigation("#scrollContainerSmall", ".cardSmall");
    }
  }

  function nextSelection() {
    if (currentPageId === p01.id) {
      handleCardNavigation("#scrollContainer", ".card", false);
    } else if (currentPageId === p02.id) {
      handleCardNavigation("#scrollContainerSmall", ".cardSmall", false);
    }
  }

  // Helper function to handle card selection for both containers
  function handleCardNavigation(containerId, cardClass, isPrev = true) {
    if (isRecording === true) {
      console.log("is recording, cannot navigate, returning");
      return;
    }

    // Get all cards in the specified container
    const cards = document.querySelectorAll(`${containerId} ${cardClass}`);

    if (cards.length === 0) {
      console.warn("No cards found in container, returning");
      return;
    }

    if (!currentCardSelected) {
      // If no card is selected, select the first one
      if (isPrev === false) {
        currentCardSelected = cards[0];
        currentCardSelected.classList.add("selected");
      }
    } else {
      // Check if the current selected card is in this container
      const isCardInContainer = Array.from(cards).includes(currentCardSelected);

      if (!isCardInContainer) {
        // If card is not in this container, select the first/last card
        if (isPrev === true) {
          currentCardSelected = cards[0];
          currentCardSelected.classList.add("selected");
          return;
        }
      }

      // Find the index of the current selected card
      const currentIndex = Array.from(cards).indexOf(currentCardSelected);
      // Remove selection from current card
      currentCardSelected.classList.remove("selected");

      // Calculate the next index based on direction
      const nextIndex = isPrev ? currentIndex - 1 : currentIndex + 1;

      // Check if the next index is out of bounds
      if (nextIndex < 0) {
        currentCardSelected = null;
      } else if (nextIndex >= cards.length) {
        // Stay on the last card instead of setting to null
        currentCardSelected = cards[cards.length - 1];
        currentCardSelected.classList.add("selected");
      } else {
        currentCardSelected = cards[nextIndex];
        currentCardSelected.classList.add("selected");

        // Ensure the selected card is visible
        currentCardSelected.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }
    }
  }

  function resetNavigation() {
    currentCardSelected = 0;
    currentPageId = p01.id;
    showPage(currentPageId);
  }

  function doAction() {

    if (currentPageId === p01.id) {
      if (currentCardSelected) {
        handleCardSelection(currentCardSelected);
      } else {
        showPage(p02.id);
      }
    } else if (currentPageId === p02.id) {
      if (isRecording === true) {
        console.log("Key released while recording, stopping recorder");
        onRecorderStop();
        return;
      }

      if (currentCardSelected) {
        handleCardSelection(currentCardSelected);
      } else {
        onRecordButtonClick();
      }
    } else if (currentPageId === p03.id) {
      showPage(p01.id);
    }
  }

  function handleCardSelection(card) {
    const cardId = card.getAttribute("data-id");
    handleCardClick(cardId);
    card.classList.remove("selected");
    currentCardSelected = null;
  }

  function showPage(pageId) {
    Object.values(pageElements).forEach((page) => {
      page.style.display = "none";
    });

    currentCardSelected = null;

    if (pageElements[pageId]) {
      pageElements[pageId].style.display = "block";
      currentPageId = pageId;
      updatePage(pageId);
    } else {
      console.error(`Page with ID ${pageId} not found`);
    }
  }

  function updatePage(pageId) {
    hideScroll();

    if (pageId === p01.id) {
      populateScroll();
    } else if (pageId === p02.id) {
      hideErrorText();
      populateScroll(false);
    }
  }

  showPage(currentPageId);

  // Change page
  const activateButton = document.getElementById("activateButton");
  activateButton.addEventListener("click", () => {
    showPage(p02.id);
  });

  const home = document.getElementById("home");
  home.addEventListener("click", () => {
    showPage(p01.id);
  });

  window.showPage = showPage;
});

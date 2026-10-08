// Content script cho OmniTrace - Chạy trên linkedin.com

console.log("OmniTrace Content Script loaded.");

interface LinkedInProfileData {
  type: 'profile' | 'search' | 'unknown';
  name?: string;
  headline?: string;
  company?: string;
  location?: string;
  profiles?: any[];
}

function scrapeLinkedInProfile(): LinkedInProfileData {
  const data: LinkedInProfileData = { type: 'profile' };

  try {
    // Lấy tên
    const nameElement = document.querySelector('h1.text-heading-xlarge') as HTMLElement;
    if (nameElement) {
      data.name = nameElement.innerText.trim();
    }

    // Lấy chức vụ (headline)
    const headlineElement = document.querySelector('.text-body-medium.break-words') as HTMLElement;
    if (headlineElement) {
      data.headline = headlineElement.innerText.trim();
    }

    // Lấy công ty (cách 1)
    const companyElement = document.querySelector('.pv-text-details__right-panel .inline-show-more-text') as HTMLElement;
    if (companyElement) {
      data.company = companyElement.innerText.trim();
    } else {
      // Cách 2: Lấy từ phần kinh nghiệm
      const expCompanyElement = document.querySelector('#experience ~ .pvs-list__outer-container .display-flex.align-items-center span.visually-hidden') as HTMLElement;
      if (expCompanyElement) {
         // Thông thường format là: "Company Name · Full-time"
         let companyText = expCompanyElement.innerText.trim();
         if (companyText.includes('·')) {
            companyText = companyText.split('·')[0].trim();
         }
         data.company = companyText;
      }
    }
  } catch (error) {
    console.error("Error scraping LinkedIn profile:", error);
  }

  return data;
}

function scrapeLinkedInSearch(): LinkedInProfileData {
  const data: LinkedInProfileData = { type: 'search', profiles: [] };

  try {
    const listItems = document.querySelectorAll('ul.reusable-search__entity-result-list li.reusable-search__result-container');
    listItems.forEach(item => {
      const profileInfo: any = {};
      
      const nameElement = item.querySelector('.entity-result__title-text a span[dir="ltr"]') as HTMLElement;
      if (nameElement) {
        // Loại bỏ các thẻ ẩn
        let name = nameElement.innerText.trim();
        const hiddenElement = nameElement.querySelector('.visually-hidden') as HTMLElement;
        if(hiddenElement) {
           name = name.replace(hiddenElement.innerText, '').trim();
        }
        profileInfo.name = name;
      }

      const headlineElement = item.querySelector('.entity-result__primary-subtitle') as HTMLElement;
      if (headlineElement) {
        profileInfo.headline = headlineElement.innerText.trim();
      }
      
      const locationElement = item.querySelector('.entity-result__secondary-subtitle') as HTMLElement;
      if (locationElement) {
        profileInfo.location = locationElement.innerText.trim();
      }

      const linkElement = item.querySelector('.entity-result__title-text a') as HTMLAnchorElement;
      if (linkElement) {
          profileInfo.url = linkElement.href;
      }

      if (profileInfo.name) {
        data.profiles?.push(profileInfo);
      }
    });
  } catch (error) {
    console.error("Error scraping LinkedIn search:", error);
  }

  return data;
}

function scrapeData(): LinkedInProfileData {
  const url = window.location.href;
  
  if (url.includes('linkedin.com/in/')) {
    return scrapeLinkedInProfile();
  } else if (url.includes('linkedin.com/search/results/')) {
    return scrapeLinkedInSearch();
  }
  
  return { type: 'unknown' };
}

// Lắng nghe yêu cầu từ popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "SCRAPE_LINKEDIN") {
    console.log("Received SCRAPE_LINKEDIN message");
    const data = scrapeData();
    sendResponse({ success: true, data });
  }
  return true; // Giữ kết nối để gửi phản hồi bất đồng bộ nếu cần
});

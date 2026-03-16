function deleteFeedback(feedbackId) {
    fetch('/delete-feedback/' + feedbackId, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (response.ok) {
                window.location.href = '/feedback';
            }
        })
        .catch(error => console.log('Error:', error));
}
function addExpense(){

    let amount = document.getElementById("amount").value
    
    let currentBalance = document.getElementById("balance").innerText.replace("₹","")
    
    currentBalance = parseInt(currentBalance)
    
    let newBalance = currentBalance - amount
    
    document.getElementById("balance").innerText = "₹"+newBalance
    
    }
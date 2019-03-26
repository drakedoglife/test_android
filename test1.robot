*** settings ***
Library    AppiumLibrary
Library    Selenium2Library
*** test cases ***
case1
    open application    http://localhost:4723/wd/hub    platformName=Android    platformVersion=7.1.1    deviceName=Galaxy S5    appPackage=com.google.android.calculator    appActivity=.Calculator
    AppiumLibrary.Click Element    id=com.sec.android.app.popupcalculator:id/bt_01
    AppiumLibrary.Click Element    id=com.sec.android.app.popupcalculator:id/bt_add
    AppiumLibrary.Click Element    id=com.sec.android.app.popupcalculator:id/bt_03
    AppiumLibrary.Click Element    id=com.sec.android.app.popupcalculator:id/bt_equal
    element should contain text    com.sec.android.app.popupcalculator:id/txtCalc    1+3
    close application
case2
    open browser    https://www.baidu.com    Chrome
    Selenium2Library.Input Text    css:#kw    python
    Selenium2Library.click button    css:#su
    #Wait Until Element Contains    css:head > title    python_百度搜索
    ${res}    get title
    should be equal    ${res}    百度一下，你就知道
    close all browsers
case3
    should be equal    ${5}    ${5}
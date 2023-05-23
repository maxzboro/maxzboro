#include <LiquidCrystal.h>
#define PLSIZE 4
LiquidCrystal disp2(8,9,10,11,12,13);
LiquidCrystal disp1(2,3,4,5,6,7);

// A2 is the exit key (R)
// Special vars
int index = 0;
bool ticker = false;
const String places[PLSIZE] = {"Home", "Games", "Settings", "Debug"};
const int unDetIn = 450; // If joystick output is below unDetIn, it is detected.
const int unDetOut = 574; // If joystick output is above unDetOut, it is detected.

const char NIL = char(0); 
const char specChars[3][6]{
  {char(197),char(198),char(199),char(200),char(247),char(246)},
  {char(187),char(255),char(210),char(158),char(157),char(178)},
  {char(206),char(251),NIL,NIL,NIL,NIL}
};

// Ctrls: B - joystick button. R - return(exit)
// Special chars for WWGC)) Dim1-col Dim2-row (? - undefined)
//   0 1 2 3 4 5 Comment
// 0 ↑ ↓ → ← ◄ ► Arrows
// 1 « » § º ª ° Spec. pucntuation
// 2 R B ? ? ? ? Misc

void update(){
  delay(500);
  disp1.clear();
  disp2.clear();
}

String MathGame(bool gname){
  if(gname){return "MathForKids";}
  while(!(digitalRead(A2))){
    disp1.print("dklklsd");
    update();
  }
}
String CarsGame(bool gname){
  if(gname){return "Dodge-A-Box";}
}
String DOOMino(bool gname){
  if(gname){return "Textelvania";}
}

typedef String (*FunctionPointer)(bool);
int gamepick = 0;
FunctionPointer games[] = {MathGame, CarsGame, DOOMino};

void setup()
{
  disp1.begin(16,2);
  disp2.begin(16,2);
  disp1.print("WWGC)) v. 0.0.0");
  disp2.print("By WhiskeredSun");
  delay(500);
  update();
}

void loop(){
  if(index>0){disp1.print(specChars[0][4]);}
  disp1.print(places[index]);
  if(index<PLSIZE-1){disp1.print(specChars[0][5]);}
  if(ticker){
  	if((index>0)&&(analogRead(A0)<unDetIn)){index--;}
  	if((index<PLSIZE-1)&&(analogRead(A0)>unDetOut)){index++;}
  }
  
  if(index==0){
    disp1.setCursor(0,1);
    disp1.print("Charge: inf%");
    disp2.print("Date: 20/05/2023");
    disp2.setCursor(0,1);
    disp2.print("Time: 18:00");
  } else if(index==1) {
    disp1.setCursor(0,1);
    int arraySize = sizeof(games) / sizeof(games[0]);
    int rticker = 0;
    disp1.print(specChars[0][2]);
    for(int x=gamepick;x<gamepick+3;x++){
      if(x==arraySize){break;}
      if(rticker==0){disp1.print(games[x](true));}
      else{disp2.setCursor(0,rticker-1);disp2.print(games[x](true));}
      rticker++;
    }
    if(digitalRead(A1)){games[gamepick](false);}
  } else if(index==3){
    disp1.setCursor(0,1);
    disp1.print(String(specChars[2][0])+" - start");
    disp2.print("Displays all exi");
    disp2.setCursor(0,1);
    disp2.print("sting characters");
    if(digitalRead(A2)){
      disp1.clear();
      disp2.clear();
      for(int x=0; x<4; x++){
        for(int y=0; y<16; y++){disp1.print(char(64*x+y));}
        disp1.setCursor(0,1);
        for(int y=0; y<16; y++){disp1.print(char(64*x+y+16));}
        for(int y=0; y<16; y++){disp2.print(char(64*x+y+32));}
        disp2.setCursor(0,1);
        for(int y=0; y<16; y++){disp2.print(char(64*x+y+48));}
        delay(1500);
        update();
      }
    }
  }
  
  ticker = !ticker;
  update();
}
